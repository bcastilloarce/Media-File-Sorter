import psutil
import vlc
import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("VideoSorter")

class VideoSorter:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Sorter")
        self.root.geometry("600x400")
        
        # Initialize variables
        self.selected_file = ""
        self.video_files = []
        self.selected_videos = {}
        self.detection_cancelled = False
        self.vlc_instance = None
        
        # Create UI elements
        self.create_widgets()
    
    def create_widgets(self):
        """Create and initialize all UI widgets"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, 
            variable=self.progress_var, 
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        # Status label
        self.status_label = ttk.Label(
            main_frame, 
            text="Detecting VLC playlist...",
            wraplength=580
        )
        self.status_label.pack(pady=10)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        # Cancel button
        self.cancel_button = ttk.Button(
            button_frame, 
            text="Cancel", 
            command=self.cancel_detection
        )
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        
        # Start detection in a separate thread to keep UI responsive
        threading.Thread(target=self.detect_vlc_playlist, daemon=True).start()
    
    def update_status(self, message):
        """Update status label safely from any thread"""
        if not self.detection_cancelled:
            self.root.after(0, lambda: self.status_label.config(text=message))
    
    def update_progress(self, value):
        """Update progress bar safely from any thread"""
        if not self.detection_cancelled:
            self.root.after(0, lambda: self.progress_var.set(value))
    
    def detect_vlc_playlist(self):
        """Detect if VLC is running and has a playlist loaded"""
        try:
            self.update_status("Searching for VLC process...")
            
            # Look for VLC process
            vlc_process = None
            for process in psutil.process_iter(['pid', 'name']):
                if self.detection_cancelled:
                    return
                
                try:
                    if 'vlc' in process.info['name'].lower():
                        vlc_process = process
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            if vlc_process:
                self.update_status(f"VLC found (PID: {vlc_process.pid}). Attempting to access playlist...")
                
                try:
                    # Create VLC instance without opening a window
                    self.vlc_instance = vlc.Instance('--no-xlib')
                    
                    # Try to get the current playlist
                    # Note: This is a simplified approach and may not work in all scenarios
                    # A more robust solution would require deeper integration with VLC's API
                    media_list_player = self.vlc_instance.media_list_player_new()
                    media_list = self.vlc_instance.media_list_new()
                    
                    # Check if we can access the playlist
                    if media_list.count() == 0:
                        self.update_status("No playlist found in VLC or unable to access it.")
                        self.root.after(0, self.show_load_options)
                    else:
                        self.update_status("Playlist detected in VLC.")
                        self.root.after(0, lambda: self.process_playlist(media_list))
                except Exception as e:
                    logger.error(f"Error accessing VLC playlist: {str(e)}")
                    self.update_status(f"Error accessing VLC playlist: {str(e)}")
                    self.root.after(0, self.show_load_options)
            else:
                self.update_status("VLC is not running.")
                self.root.after(0, self.show_load_options)
        except Exception as e:
            logger.error(f"Error in detect_vlc_playlist: {str(e)}")
            self.update_status(f"Error detecting VLC: {str(e)}")
            self.root.after(0, self.show_load_options)
    
    def process_playlist(self, media_list):
        """Process the detected VLC playlist"""
        try:
            self.update_status("Processing playlist...")
            self.update_progress(0)
            
            # Create a directory for saving playlists if it doesn't exist
            playlists_dir = os.path.join(os.path.expanduser("~"), "VideoSorter_Playlists")
            os.makedirs(playlists_dir, exist_ok=True)
            
            # Save the playlist to a file
            playlist_path = os.path.join(playlists_dir, "exported_playlist.m3u")
            
            with open(playlist_path, "w", encoding="utf-8") as f:
                count = media_list.count()
                for i in range(count):
                    if self.detection_cancelled:
                        return
                    
                    try:
                        media = media_list.item_at_index(i)
                        mrl = media.get_mrl()
                        f.write(mrl + "\n")
                        
                        # Add to our internal list
                        self.video_files.append(mrl)
                        
                        # Update progress
                        progress = (i + 1) / count * 100
                        self.update_progress(progress)
                    except Exception as e:
                        logger.warning(f"Error processing item {i}: {str(e)}")
            
            self.update_status(f"Playlist processed and saved to {playlist_path}")
            self.show_video_list()
        except Exception as e:
            logger.error(f"Error processing playlist: {str(e)}")
            self.update_status(f"Error processing playlist: {str(e)}")
    
    def show_video_list(self):
        """Display the list of videos from the playlist"""
        # Clear existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create new layout for video list
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text="Processed Videos", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Create scrollable frame for videos
        container = ttk.Frame(main_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add videos to the list
        for i, video_path in enumerate(self.video_files):
            # Extract filename from path
            filename = os.path.basename(video_path.replace("file://", ""))
            
            # Create a frame for each video
            video_frame = ttk.Frame(scrollable_frame)
            video_frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Add checkbox for selection
            var = tk.BooleanVar()
            checkbox = ttk.Checkbutton(
                video_frame, 
                text=filename, 
                variable=var,
                command=lambda v=video_path, var=var: self.toggle_video_selection(v, var)
            )
            checkbox.pack(side=tk.LEFT, padx=5)
            
            # Store reference to the checkbox variable
            self.selected_videos[video_path] = var
        
        # Add buttons at the bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame, 
            text="Process Selected", 
            command=self.process_selected_videos
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="Load Another Playlist", 
            command=self.restart_application
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="Exit", 
            command=self.root.destroy
        ).pack(side=tk.LEFT, padx=5)
    
    def toggle_video_selection(self, video_path, var):
        """Handle video selection/deselection"""
        # This method is called when a checkbox is toggled
        pass
    
    def process_selected_videos(self):
        """Process the videos that have been selected by the user"""
        selected = [path for path, var in self.selected_videos.items() if var.get()]
        
        if not selected:
            messagebox.showinfo("No Selection", "Please select at least one video to process.")
            return
        
        # Here you would implement the actual video processing logic
        messagebox.showinfo(
            "Processing", 
            f"Processing {len(selected)} videos. This feature is under development."
        )
    
    def cancel_detection(self):
        """Cancel the detection process"""
        self.detection_cancelled = True
        self.update_status("Detection cancelled.")
        
        # Clean up VLC instance if it exists
        if self.vlc_instance:
            del self.vlc_instance
            self.vlc_instance = None
        
        # Ask if user wants to exit or try again
        if messagebox.askyesno("Cancel", "Detection cancelled. Do you want to exit?"):
            self.root.destroy()
        else:
            self.restart_application()
    
    def restart_application(self):
        """Restart the application to its initial state"""
        # Clean up
        self.detection_cancelled = True
        if self.vlc_instance:
            del self.vlc_instance
            self.vlc_instance = None
        
        # Clear all widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Reset variables
        self.selected_file = ""
        self.video_files = []
        self.selected_videos = {}
        self.detection_cancelled = False
        
        # Recreate UI
        self.create_widgets()
        
        # Start detection again
        threading.Thread(target=self.detect_vlc_playlist, daemon=True).start()
    
    def show_load_options(self):
        """Show options for manually loading a playlist"""
        if self.detection_cancelled:
            return
        
        # Clear existing buttons
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Button) and widget != self.cancel_button:
                widget.destroy()
        
        # Create a frame for the options
        options_frame = ttk.Frame(self.root)
        options_frame.pack(pady=10)
        
        # Add options
        ttk.Button(
            options_frame, 
            text="Start VLC", 
            command=self.start_vlc
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            options_frame, 
            text="Load M3U Playlist", 
            command=self.load_manual_m3u
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            options_frame, 
            text="Retry Detection", 
            command=self.restart_application
        ).pack(side=tk.LEFT, padx=5)
    
    def start_vlc(self):
        """Start VLC in a platform-independent way"""
        try:
            self.update_status("Starting VLC...")
            
            # Platform-specific VLC launching
            if sys.platform.startswith('darwin'):  # macOS
                os.system("open -a VLC")
            elif sys.platform.startswith('win'):   # Windows
                os.system("start vlc")
            else:  # Linux and others
                os.system("vlc &")
            
            self.update_status("VLC started. Please load your playlist in VLC.")
            messagebox.showinfo(
                "VLC Started", 
                "Please load your playlist in VLC, then click 'Retry Detection'."
            )
        except Exception as e:
            logger.error(f"Error starting VLC: {str(e)}")
            self.update_status(f"Error starting VLC: {str(e)}")
            messagebox.showerror("Error", f"Could not start VLC: {str(e)}")
    
    def load_manual_m3u(self):
        """Load a playlist file manually"""
        try:
            file_path = filedialog.askopenfilename(
                title="Select M3U Playlist",
                filetypes=[
                    ("Playlist Files", "*.m3u *.m3u8"),
                    ("All Files", "*.*")
                ]
            )
            
            if not file_path:
                return  # User cancelled
            
            self.selected_file = file_path
            self.update_status(f"Loading playlist: {os.path.basename(file_path)}")
            
            # Process the playlist in a separate thread
            threading.Thread(
                target=self.process_manual_playlist,
                args=(file_path,),
                daemon=True
            ).start()
        except Exception as e:
            logger.error(f"Error loading playlist: {str(e)}")
            self.update_status(f"Error loading playlist: {str(e)}")
            messagebox.showerror("Error", f"Could not load playlist: {str(e)}")
    
    def process_manual_playlist(self, file_path):
        """Process a manually loaded playlist file"""
        try:
            self.update_status(f"Processing playlist: {os.path.basename(file_path)}")
            self.update_progress(0)
            
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            
            # Filter out comments and empty lines, keep only media URLs
            self.video_files = []
            total_lines = len(lines)
            
            for i, line in enumerate(lines):
                if self.detection_cancelled:
                    return
                
                line = line.strip()
                if line and not line.startswith('#'):
                    self.video_files.append(line)
                
                # Update progress
                progress = (i + 1) / total_lines * 100
                self.update_progress(progress)
            
            self.update_status(f"Processed {len(self.video_files)} videos from playlist.")
            self.root.after(0, self.show_video_list)
        except Exception as e:
            logger.error(f"Error processing playlist file: {str(e)}")
            self.update_status(f"Error processing playlist: {str(e)}")
            messagebox.showerror("Error", f"Could not process playlist: {str(e)}")

def main():
    """Main entry point for the application"""
    try:
        # Set up the root window
        root = tk.Tk()
        root.title("Video Sorter")
        
        # Set window icon if available
        try:
            if sys.platform.startswith('win'):
                root.iconbitmap("icon.ico")
            else:
                logo = tk.PhotoImage(file="icon.png")
                root.iconphoto(True, logo)
        except:
            pass  # Icon not critical, continue without it
        
        # Create the application
        app = VideoSorter(root)
        
        # Start the main loop
        root.mainloop()
    except Exception as e:
        logger.critical(f"Application error: {str(e)}")
        messagebox.showerror("Critical Error", f"An unexpected error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()