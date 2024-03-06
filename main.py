from PyQt6 import QtWidgets

from client.s3 import S3Client
from gui.gui import MainWindow


def main() -> None:
    """
    Main function to initialize the S3 client, set up the GUI, and start the application.
    """
    try:
        # Initialize the S3 client with the configuration file
        s3_client: S3Client = S3Client("config.json")
    except Exception as e:
        print(f"Failed to initialize S3 client: {e}")
        return

    try:
        # Create a new Qt application
        app: QtWidgets.QApplication = QtWidgets.QApplication([])
        app.setStyle("Fusion")

        # Create the main window for the application
        window: MainWindow = MainWindow(s3_client)
        window.show()

        # Execute the application
        app.exec()
    except Exception as e:
        print(f"Failed to start the application: {e}")


if __name__ == "__main__":
    main()
