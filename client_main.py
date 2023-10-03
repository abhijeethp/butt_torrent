import threading
from client import Client
class ClientCLI:

    def __init__(self):
        self.client = Client(dir_name=input("Enter disk name to mount: "))
        self.downloads_in_progress = {}

        self.menu_options = {
            "1": ("List files", self.list_files),
            "2": ("Download a file", self.download_file),
            "3": ("Show active downloads", self.show_active_downloads),
        }

    def run(self):
        while True:
            print("\nOptions:", *(f"{k}. {v[0]}" for k, v in self.menu_options.items()), sep="\n")
            choice = input("Enter choice: ")
            self.menu_options.get(choice, (None, lambda: print("Invalid choice!")))[1]()

    def list_files(self):
        resp = self.client.file_list()
        for i, file in enumerate(resp.files, start=1):
            print(f"{i}. {file['name']} ({file['length']} bytes)")

    def download_file(self):
        file_name = input("Enter file name to download: ")
        download_thread = threading.Thread(target=self.client.download_file, args=(file_name,))
        self.downloads_in_progress[file_name] = download_thread
        download_thread.start()

    def show_active_downloads(self):
        active_downloads = [file_name for file_name, thread in self.downloads_in_progress.items() if thread.is_alive()]
        for file_name in active_downloads:
            progress = self.client.get_download_progress(file_name)
            print(f"Downloading: {file_name} - {progress}% complete")

if __name__ == "__main__":
    ClientCLI().run()