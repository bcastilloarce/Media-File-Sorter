import psutil
import vlc
import os
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

class VideoSorter:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Sorter")
        self.root.geometry("600x400")

        self.selected_file = ""
        self.video_files = []
        self.selected_videos = {}

        self.create_widgets()

    def create_widgets(self):
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=10)

        self.status_label = tk.Label(self.root, text="Detecting VLC playlist...")
        self.status_label.pack()

        self.cancel_button = tk.Button(self.root, text="Cancel", command=self.cancel_detection)
        self.cancel_button.pack()

        self.detect_vlc_playlist()

    def detect_vlc_playlist(self):
        # Buscar el proceso de VLC en ejecución
        vlc_process = None
        for process in psutil.process_iter(['pid', 'name']):
            if 'vlc' in process.info['name'].lower():
                vlc_process = process
                break

        if vlc_process:
            # Obtener la lista de reproducción de VLC
            instance = vlc.Instance('--no-xlib')
            player = instance.media_player_new()
            player.set_mrl('vlc://quit')  # Evitar que VLC abra una ventana
            media_list = player.get_media_player().get_media_list()
            num_items = media_list.count()

            if num_items == 0:
                self.status_label.config(text="No playlist found in VLC.")
                self.show_load_options()
            else:
                self.status_label.config(text="Playlist detected in VLC.")
                self.process_playlist(media_list)
        else:
            self.status_label.config(text="VLC is not running.")
            self.show_load_options()

    def process_playlist(self, media_list):
        # Procesar la lista de reproducción de VLC
        self.status_label.config(text="Processing playlist...")
        self.progress_var.set(0)

        # Ejemplo: Guardar la lista en un archivo .m3u
        with open("Lista.m3u", "w") as f:
            for i in range(media_list.count()):
                media = media_list.item_at_index(i)
                f.write(media.get_mrl() + "\n")
                progress = (i + 1) / media_list.count() * 100
                self.progress_var.set(progress)
                self.root.update_idletasks()

        self.status_label.config(text="Playlist processed.")

    def cancel_detection(self):
        self.root.destroy()

    def show_load_options(self):
        # Mostrar opciones para cargar manualmente una lista de reproducción
        messagebox.showinfo("No Playlist Found", "No playlist found in VLC.")
        choice = messagebox.askyesno("Load Playlist", "Do you want to load a playlist in VLC?")
        if choice:
            os.system("open -a VLC")
            messagebox.showinfo("Load Playlist", "Please load the playlist in VLC and click 'Reload' to retry.")
            self.status_label.config(text="Waiting for playlist to be loaded...")
            self.cancel_button.config(text="Cancel", command=self.cancel_detection)
            self.reload_button = tk.Button(self.root, text="Reload", command=self.detect_vlc_playlist)
            self.reload_button.pack()
            self.load_manual_button = tk.Button(self.root, text="Load Manual M3U", command=self.load_manual_m3u)
            self.load_manual_button.pack()
        else:
            self.cancel_detection()

    def load_manual_m3u(self):
        # Cargar manualmente un archivo .m3u
        file_path = filedialog.askopenfilename(filetypes=[("M3U Files", "*.m3u")])
        if file_path:
            self.status_label.config(text="Playlist loaded manually.")
            self.selected_file = file_path
            self.process_manual_playlist()

    def process_manual_playlist(self):
        # Procesar la lista de reproducción cargada manualmente
        self.status_label.config(text="Processing playlist...")

        # Ejemplo: Leer el archivo .m3u y procesarlo
        with open(self.selected_file, "r") as f:
            lines = f.readlines()
            self.video_files = [line.strip() for line in lines]

        self.status_label.config(text="Playlist processed.")

def main():
    root = tk.Tk()
    app = VideoSorter(root)
    root.mainloop()

if __name__ == "__main__":
    main()
