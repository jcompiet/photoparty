# PhotoParty: Dynamic Slideshow using Filegator to upload images

This project is a Flask-based slideshow that automatically updates with images from a specified directory. Perfect for parties and events!

## Key Features

-   **Dynamic Updates:** New images added to the directory are automatically displayed in the slideshow.
-   **Customizable:** Configure transition times, sync intervals, and sorting order via environment variables.
-   **Filegator Integration:** Use [Filegator](https://filegator.io/) (or any file management system) to allow party guests to easily upload their photos directly to the designated directory.
-   **Easy Deployment:** Designed for easy deployment with Docker.

## Setup

### Prerequisites

-   Docker
-   Docker Compose

### Configuration

1.  **Clone the repository:**

    ```
    git clone [repository-url]
    cd photoparty
    ```

2.  **Environment Variables:**

    Configure the following environment variables in your `docker-compose.yml` or `.env` file:

    -   `PHOTO_TRANSITION_TIME`: Time between photo transitions (in milliseconds). Default is 4000.
    -   `SYNC_INTERVAL`: Time between syncing the photos directory (in milliseconds). Default is 10000.
    -   `PHOTOS_DIRECTORY`: The directory where the images are stored. This is **required**.
    -   `SLIDESHOW_TITLE`: The title of the slideshow. Default is "Default Slideshow Title".
    -   `SORT_ORDER`: Sorting order for the images. Options are `"recent"`, `"alphabetical"`, or `"random"`. Default is `"recent"`.

    Example `docker-compose.yml`:

    ```
    version: '3.8'
    services:
        photoparty:
            image: photoparty
            container_name: photoparty
            ports:
                - "5000:5000"
            volumes:
                - /path/to/your/photos:/mnt/photos
                - /path/to/your/storage:/app/storage
            environment:
                PHOTO_TRANSITION_TIME: 5000
                SYNC_INTERVAL: 15000
                PHOTOS_DIRECTORY: /mnt/photos
                SLIDESHOW_TITLE: "Party Slideshow!"
                SORT_ORDER: random
    ```

3.  **Filegator Setup:**

    -   Deploy Filegator separately and configure it to upload files to the directory specified by `PHOTOS_DIRECTORY`.
    -   Ensure that the user configured in Filegator has write access to the `PHOTOS_DIRECTORY`.

### Running the Application

1.  **Build and Run with Docker Compose:**

    ```
    docker-compose up --build
    ```

2.  **Access the Slideshow:**

    Open your web browser and navigate to `http://localhost:5000`.

## Usage

1.  **Upload Images:** Use Filegator to upload images to the directory specified by `PHOTOS_DIRECTORY`.
2.  **Watch the Slideshow:** The slideshow will automatically update as new images are added.

## Contributing

Feel free to contribute to this project by submitting pull requests or opening issues.

## License

[Your License]
