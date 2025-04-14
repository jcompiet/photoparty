from flask import Flask, render_template_string, url_for, jsonify
import os
import shutil
import filecmp
import logging
import random
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Initialize Flask app
app = Flask(__name__, static_folder="storage", static_url_path="/storage")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Read environment variables
PHOTO_TRANSITION_TIME = int(os.getenv("PHOTO_TRANSITION_TIME", 4000))  # Default: 4000ms
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", 10000))  # Default: 10000ms
PHOTOS_DIRECTORY = os.getenv("PHOTOS_DIRECTORY")  # Required environment variable
SLIDESHOW_TITLE = os.getenv("SLIDESHOW_TITLE", "Default Slideshow Title")

# Validate PHOTOS_DIRECTORY
if not PHOTOS_DIRECTORY:
    raise ValueError("The environment variable PHOTOS_DIRECTORY must be set.")
if not os.path.exists(PHOTOS_DIRECTORY):
    raise ValueError(f"The directory specified in PHOTOS_DIRECTORY ({PHOTOS_DIRECTORY}) does not exist.")

# Disable caching globally for dynamic content
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# HTML template for the slideshow
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ slideshow_title }}</title>
    <link rel="icon" type="image/png" href="{{ url_for('static', filename='icon.png') }}">
    <style>
        body {
            margin: 0;
            background-color: black;
            overflow: hidden;
        }
        .header-bar {
            position: absolute;
            top: 0;
            width: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            font-size: 18px;
            padding: 10px;
            display: flex;
            justify-content: space-between;
            z-index: 1;
        }
        #status {
            position: fixed;
            bottom: 20px;
            left: 20px;
            color: white;
            font-size: 16px;
            background-color: rgba(0, 0, 0, 0.7);
            padding: 8px 15px;
            border-radius: 5px;
            z-index: 2;
            display: none; /* Hidden by default */
        }
        .slideshow-container {
            position: relative;
            width: 100%;
            height: 100vh;
        }
        .slide {
            position: absolute;
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        .slide.active {
            opacity: 1;
        }
        .slide {
            opacity: 0;
            transition: opacity 1.5s ease-in-out;
        }
    </style>
</head>
<body>
    {% if photos %}
        <div class="header-bar">
            <div id="counter">Aantal afbeeldingen: {{ photos | length }}</div>
        </div>

        <!-- Slideshow Container -->
        <div class="slideshow-container" id="slideshow-container">
            {% for photo in photos %}
                <img class="slide{% if loop.first %} active{% endif %}" src="{{ photo }}">
            {% endfor %}
        </div>

        <!-- Status message -->
        <div id="status"></div>

        <!-- Audio elements -->
        <audio id="add-sound" src="{{ url_for('static', filename='sounds/add_chime.mp3') }}"></audio>
        <audio id="remove-sound" src="{{ url_for('static', filename='sounds/remove_chime.mp3') }}"></audio>

        <script>
            let photos = {{ photos | safe }};
            let currentIndex = 0;

            // Use environment variables passed from Flask
            const photoTransitionTime = {{ photo_transition_time }};
            const syncInterval = {{ sync_interval }};
            
            let slideshowInterval;

            function startSlideshow() {
                // Clear any existing interval
                if (slideshowInterval) {
                    clearInterval(slideshowInterval);
                }

                // Restart slideshow from the beginning
                currentIndex = 0;

                const slides = document.querySelectorAll('.slide');
                slides.forEach(slide => slide.classList.remove('active')); // Reset all slides

                if (slides.length > 0) {
                    slides[0].classList.add('active'); // Start with the first slide
                }

                slideshowInterval = setInterval(() => {
                    slides[currentIndex].classList.remove('active');
                    currentIndex = (currentIndex + 1) % slides.length; // Wrap around index
                    slides[currentIndex].classList.add('active');
                }, photoTransitionTime);
            }

            function fetchUpdatedPhotos() {
                fetch("/photos")
                    .then(response => response.json())
                    .then(data => {
                        const status = document.getElementById('status');
                        const counter = document.getElementById('counter');
                        const addSound = document.getElementById('add-sound');
                        const removeSound = document.getElementById('remove-sound');

                        // Update counter with accurate image count
                        counter.textContent = `Aantal afbeeldingen: ${data.count}`;

                        if (data.added > 0 || data.removed > 0) { // Only restart if changes occurred
                            if (data.added > 0) {
                                status.textContent = `Afbeeldingen toegevoegd (${data.added})`;
                                status.style.display = "block";
                                playSound(addSound);
                                setTimeout(() => { status.style.display = "none"; }, 5000);
                            }
                            if (data.removed > 0) {
                                status.textContent = `Afbeeldingen verwijderd (${data.removed})`;
                                status.style.display = "block";
                                playSound(removeSound);
                                setTimeout(() => { status.style.display = "none"; }, 5000);
                            }

                            updateSlideshow(data.photos); // Update slideshow with new photo list
                        } else {
                            console.log("No changes detected during sync.");
                        }
                    })
                    .catch(error => console.error("Error fetching new photos:", error));
        }

            function preloadAudio(audioElement) {
                audioElement.load();
                console.log(`Preloaded audio file ${audioElement.src}`);
            }

            function playSound(audioElement) {
                try {
                    audioElement.pause(); // Ensure no overlapping playback
                    audioElement.currentTime = 0; // Reset to start
                    audioElement.play().catch(error => {
                        console.error(`Error playing sound ${audioElement.src}:`, error);
                    });
                } catch (error) {
                    console.error(`Error handling sound ${audioElement.src}:`, error);
                }
            }

            preloadAudio(document.getElementById('add-sound'));
            preloadAudio(document.getElementById('remove-sound'));

            // Start initial slideshow
            startSlideshow();

            // Periodically fetch updated photos and restart slideshow only if needed
            setInterval(fetchUpdatedPhotos, syncInterval);
        </script>
    {% else %}
        <p>No images found in the directory.</p>
    {% endif %}
</body>
</html>
"""

@app.route("/")
def slideshow():
    # Construct the full path to the storage/photos directory
    photos_dir = os.path.join(app.static_folder, 'photos')

    # Ensure the destination directory exists
    if not os.path.exists(photos_dir):
        os.makedirs(photos_dir)

    # Sync photos from the source directory to the storage directory
    sync_photos(PHOTOS_DIRECTORY, photos_dir)

    # Get list of image files in the directory
    photos = []
    for file in os.listdir(photos_dir):
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            file_path = os.path.join(photos_dir, file)
            if os.path.exists(file_path):
                # Use url_for to generate the correct URL for the static file
                photo_url = url_for('static', filename=f'photos/{file}')
                photos.append({
                    "url": f"{photo_url}?t={int(os.path.getmtime(file_path))}",
                    "mtime": os.path.getmtime(file_path)
                })

    # Sort photos by modification time in descending order
    photos = sorted(photos, key=lambda x: x["mtime"], reverse=True)

    # Extract only the URLs
    photo_urls = [photo["url"] for photo in photos]

    return render_template_string(
        HTML_TEMPLATE,
        photos=photo_urls,
        photo_transition_time=PHOTO_TRANSITION_TIME,
        sync_interval=SYNC_INTERVAL,
        slideshow_title=SLIDESHOW_TITLE
    )

@app.route("/photos")
def get_photos():
    # Return updated photo list as JSON for dynamic updates
    photos_dir = "storage/photos"  # Updated to reflect new static directory
    added, removed = sync_photos(PHOTOS_DIRECTORY, photos_dir)

    # Get list of image files in the directory with cache-busting timestamps
    photos = []
    for file in os.listdir(photos_dir):
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):  # Filter image files
            file_path = os.path.join(photos_dir, file)
            if os.path.isfile(file_path):  # Ensure it's a file
                photos.append({
                    "url": f"{url_for('static', filename=file)}?t={int(os.path.getmtime(file_path))}",
                    "mtime": os.path.getmtime(file_path)  # Include modification time for sorting
                })

    # Determine sorting order based on environment variable
    sort_order = os.getenv("SORT_ORDER", "recent")  # Default to "recent"

    if sort_order == "recent":
        # Sort by modification time (descending)
        photos_sorted = sorted(photos, key=lambda x: x["mtime"], reverse=True)
    elif sort_order == "alphabetical":
        # Sort alphabetically by filename
        photos_sorted = sorted(photos, key=lambda x: x["url"])
    elif sort_order == "random":
        # Shuffle the list for random order
        random.shuffle(photos)
        photos_sorted = photos

    # Extract URLs from sorted photos
    photo_urls = [photo["url"] for photo in photos_sorted]

    return jsonify({
        "photos": photo_urls,
        "added": added,
        "removed": removed,
        "count": len(photo_urls)  # Include accurate count of images
    })

def sync_photos(source_dir, dest_dir):
    """
    Sync files from source directory to destination directory.
    Adds or updates new files and removes files that no longer exist in the source.
    """
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    # Normalize filenames and filter valid image files
    source_files = {
        normalize_filename(file): file
        for file in os.listdir(source_dir)
        if file.lower().endswith(('.jpg', '.jpeg', '.png'))
    }
    dest_files = set(os.listdir(dest_dir))

    added_count = len(source_files.keys() - dest_files)
    removed_count = len(dest_files - source_files.keys())

    logging.info(f"Syncing photos - Added: {added_count}, Removed: {removed_count}")

    # Remove files that no longer exist in the source directory
    for file in dest_files - source_files.keys():
        file_path = os.path.join(dest_dir, file)
        if os.path.isfile(file_path):  # Ensure it's a file, not a directory
            os.remove(file_path)
        else:
            logging.warning(f"Skipping non-file item during cleanup: {file_path}")

    # Copy new or updated files from source to destination
    for normalized_name, original_name in source_files.items():
        source_file_path = os.path.join(source_dir, original_name)
        dest_file_path = os.path.join(dest_dir, normalized_name)
        try:
            if not os.path.exists(dest_file_path) or not filecmp.cmp(source_file_path, dest_file_path, shallow=False):
                shutil.copy2(source_file_path, dest_file_path)
        except FileNotFoundError:
            logging.warning(f"File not found: {source_file_path}. Skipping.")

    return added_count, removed_count

def normalize_filename(filename):
    """
    Normalize filenames by replacing spaces with underscores and removing special characters.
    """
    return filename.replace(" ", "_").replace("(", "").replace(")", "").replace("'", "")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
