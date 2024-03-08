import math
import os
import threading
from typing import Dict

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QFileDialog


def load_stylesheet(filename: str) -> str:
    """
    Load the stylesheet from a file.

    :param filename: The path to the stylesheet file.
    :return: The contents of the stylesheet file.
    """
    try:
        with open(filename, "r") as f:
            return f.read()
    except FileNotFoundError as e:
        print(f"Failed to load stylesheet: {e}")
        return ""


class MainWindow(QtWidgets.QMainWindow):
    url_generated = QtCore.pyqtSignal(str)

    def __init__(self, s3_client):  # Add s3_client as an argument
        """
        Initialize the main window.

        :param s3_client: The S3 client to use for S3 operations.
        """
        super().__init__()

        self.s3_client = s3_client
        self.setStyleSheet(load_stylesheet("assets/style.css"))

        # set icon
        self.setWindowIcon(QtGui.QIcon("assets/icon.ico"))

        self.setWindowTitle("R2 Explorer")
        self.listWidget = QtWidgets.QListWidget()
        self.listWidget.setFixedWidth(200)
        self.treeWidget = QtWidgets.QTreeWidget()

        self.listWidget.itemClicked.connect(self.on_bucket_select)
        self.treeWidget.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.treeWidget.customContextMenuRequested.connect(
            self.on_treeview_right_click)

        self.menu = QtWidgets.QMenu()
        self.menu.addAction("Generate URL", self.generate_url)
        self.menu.addAction("Download", self.download)
        self.menu.addAction("Delete", self.delete)

        self.populate_buckets()

        self.refreshButton = QtWidgets.QPushButton("Refresh")
        self.refreshButton.clicked.connect(self.refresh)

        self.uploadButton = QtWidgets.QPushButton("Upload")
        self.uploadButton.clicked.connect(self.upload)

        layout = QtWidgets.QHBoxLayout()  # Define layout first
        layout.addWidget(self.listWidget)

        tree_layout = (
            QtWidgets.QVBoxLayout()
        )  # New layout for the tree widget and the buttons
        tree_layout.addWidget(self.treeWidget)

        self.statusBar = self.statusBar()  # Add a status bar

        self.treeWidget.setHeaderLabels(
            ["Name", "Size", "Last Modified"]
        )  # Add headers to the tree view

        button_layout = QtWidgets.QHBoxLayout()  # New layout for the buttons
        button_layout.addWidget(self.refreshButton)
        button_layout.addWidget(self.uploadButton)
        # Add the button layout to the tree layout
        tree_layout.addLayout(button_layout)

        layout.addLayout(tree_layout)  # Add the tree layout to the main layout

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.selected_bucket = None
        self.url_generated.connect(self.on_url_generated)

        self.resize(800, 600)

    def populate_buckets(self) -> None:
        """
        Populate the list widget with the names of all buckets.
        """
        try:
            buckets = self.s3_client.list_buckets_names()
            self.listWidget.addItems(buckets)
        except Exception as e:
            print(f"Failed to populate buckets: {e}")

    def on_bucket_select(self, item: QtWidgets.QListWidgetItem) -> None:
        """
        Handle the event that a bucket is selected.

        :param item: The selected item.
        """
        self.selected_bucket = item.text()  # Modify this line
        self.treeWidget.clear()
        threading.Thread(
            target=self.populate_treeview, args=(self.selected_bucket,)
        ).start()

    def populate_treeview(self, bucket: str) -> None:
        """
        Populate the tree widget with the objects in a bucket.

        :param bucket: The name of the bucket.
        """
        try:
            objects = self.s3_client.list_objects(bucket)
            nodes = {}
            for obj in objects:
                path_parts = obj["Key"].split("/")
                size = self.convert_size(obj["Size"])  # Convert the size
                last_modified = obj["LastModified"].strftime(
                    "%d:%m:%Y %H:%M:%S"
                )  # Format the date
                parent_node = self.treeWidget
                for part in path_parts:
                    node = nodes.get(part)
                    if node is None:
                        node = QtWidgets.QTreeWidgetItem(
                            parent_node, [part, size, last_modified]
                        )
                        nodes[part] = node
                    parent_node = node
        except Exception as e:
            print(f"Failed to populate tree view: {e}")

    def convert_size(self, size_bytes: int) -> str:
        """
        Convert a size in bytes to a human-readable string.

        :param size_bytes: The size in bytes.
        :return: A human-readable string representing the size.
        """
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    def on_treeview_right_click(self, point: QtCore.QPoint) -> None:
        """
        Handle the event that the tree view is right-clicked.

        :param point: The point where the tree view was clicked.
        """
        if item := self.treeWidget.itemAt(point):
            self.menu.exec(self.treeWidget.mapToGlobal(point))

    def on_url_generated(self, url: str) -> None:
        """
        Handle the event that a URL is generated.

        :param url: The generated URL.
        """
        QtWidgets.QApplication.clipboard().setText(url)

    def refresh(self) -> None:
        """
        Refresh the tree view.
        """
        if self.selected_bucket:
            self.treeWidget.clear()
            threading.Thread(
                target=self.populate_treeview, args=(self.selected_bucket,)
            ).start()
            self.statusBar.showMessage(
                f"Bucket {self.selected_bucket} refreshed")
            self.update_storage_usage()

    def upload(self) -> None:
        """
        Upload a file to the selected bucket.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Open File")
        if filename and self.selected_bucket:
            key = os.path.basename(filename)
            threading.Thread(
                target=self.s3_client.upload_file,
                args=(self.selected_bucket, key, filename),
            ).start()
            self.statusBar.showMessage(f"File {key} uploaded successfully")

    def generate_url(self) -> None:
        """
        Generate a URL for the selected object.
        """
        item = self.treeWidget.currentItem()
        if item and self.selected_bucket and not item.text(0).endswith("/"):
            key = []
            while item:
                key.append(item.text(0))
                item = item.parent()
            key = "/".join(reversed(key))  # Construct the full path
            url = self.s3_client.generate_url(self.selected_bucket, key)
            self.url_generated.emit(url)
            self.statusBar.showMessage(
                f"URL generated for {key} successfully"
            )  # Show a message in the status bar

    def delete(self) -> None:
        """
        Delete the selected object.
        """
        item = self.treeWidget.currentItem()
        if item and self.selected_bucket:
            key = []
            while item:
                key.append(item.text(0))
                item = item.parent()
            key = "/".join(reversed(key))  # Construct the full path
            self.s3_client.delete(self.selected_bucket, key)
            self.statusBar.showMessage(
                f"File {key} deleted successfully"
            )  # Show a message in the status bar

    def download(self) -> None:
        """
        Download the selected object.
        """
        item = self.treeWidget.currentItem()
        if item and self.selected_bucket:
            key = item.text(0)
            if "/" not in key:  # Check if the file is in the root directory
                original_filename = (
                    key  # The key is the filename for files in the root directory
                )
                filename, _ = QFileDialog.getSaveFileName(
                    self, "Save File", original_filename
                )
                if filename:
                    threading.Thread(
                        target=self.s3_client.download_file,
                        args=(self.selected_bucket, key, filename),
                    ).start()
                    self.statusBar.showMessage(
                        f"File {original_filename} downloaded successfully"
                    )  # Show a message in the status bar

    def calculate_storage_usage(self, buckets: Dict[str, int]) -> float:
        """
        Calculate the total storage usage of all buckets.

        :param buckets: A dictionary mapping bucket names to their sizes in bytes.
        :return: The total storage usage in MB.
        """
        return sum(round(bucket_size / 1024 / 1024, 2) for bucket_size in buckets.values())

    def update_storage_usage(self) -> None:
        """
        Update the storage usage display.
        """
        try:
            buckets = self.s3_client.show_storage_usage()
            total_usage = self.calculate_storage_usage(buckets)
            self.statusBar.showMessage(
                f"Total storage usage: {total_usage} MB")
        except Exception as e:
            print(f"Failed to update storage usage: {e}")
