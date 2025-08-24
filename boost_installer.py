#!/usr/bin/env python3
# boost_installer.py
# made by painter3000

"""
AMD-GPU-BOOST Installer GUI
Automatisches Patching von Pinokio Apps für bessere AMD GPU Performance
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import shutil
from pathlib import Path

class BOOSTConfig:
    def __init__(self):
        self.config_file = os.path.expanduser("~/.boost_installer_config.json")
        self.default_pinokio_path = "/home/oem/pinokio/api"
        
    def load_pinokio_path(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('pinokio_path', self.default_pinokio_path)
        except:
            pass
        return self.default_pinokio_path
        
    def save_pinokio_path(self, path):
        try:
            config = {'pinokio_path': path}
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Config save error: {e}")

class BOOSTInstaller:
    def __init__(self):
        self.config = BOOSTConfig()
        self.pinokio_path = self.config.load_pinokio_path()
        self.apps = []
        
        self.setup_gui()
        self.auto_scan()
        
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("AMD-GPU-BOOST Installer v1.0")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Main Frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Settings Frame
        settings_frame = ttk.Frame(main_frame)
        settings_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0,10))
        
        ttk.Label(settings_frame, text="Pinokio Path:").grid(row=0, column=0, sticky=tk.W)
        
        self.path_var = tk.StringVar(value=self.pinokio_path)
        path_entry = ttk.Entry(settings_frame, textvariable=self.path_var, width=50)
        path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5,0))
        
        ttk.Button(settings_frame, text="⚙️", command=self.change_path, width=3).grid(row=0, column=2, padx=(5,0))
        
        settings_frame.columnconfigure(1, weight=1)
        
        # Apps List Frame
        list_frame = ttk.LabelFrame(main_frame, text="Pinokio Apps", padding="5")
        list_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0,10))
        
        # Treeview for apps
        self.tree = ttk.Treeview(list_frame, columns=('status', 'entry', 'path'), show='tree headings', height=15)
        self.tree.heading('#0', text='App Name')
        self.tree.heading('status', text='Status')
        self.tree.heading('entry', text='Entry Point')
        self.tree.heading('path', text='Path')
        
        self.tree.column('#0', width=150)
        self.tree.column('status', width=80)
        self.tree.column('entry', width=120)
        self.tree.column('path', width=200)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Buttons Frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        ttk.Button(buttons_frame, text="🔄 Re-Scan", command=self.auto_scan).grid(row=0, column=0, padx=(0,5))
        ttk.Button(buttons_frame, text="📁 Browse...", command=self.browse_folder).grid(row=0, column=1, padx=(0,5))
        ttk.Button(buttons_frame, text="✅ Patch Selected", command=self.patch_selected).grid(row=0, column=2, padx=(0,5))
        ttk.Button(buttons_frame, text="❌ Remove Selected", command=self.remove_selected).grid(row=0, column=3, padx=(0,5))
        ttk.Button(buttons_frame, text="ℹ️ About", command=self.show_about).grid(row=0, column=4, padx=(5,0))
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10,0))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
    def change_path(self):
        new_path = filedialog.askdirectory(
            title="Select Pinokio API Directory",
            initialdir=self.pinokio_path
        )
        if new_path:
            self.pinokio_path = new_path
            self.path_var.set(new_path)
            self.config.save_pinokio_path(new_path)
            self.auto_scan()
            
    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select App Directory")
        if folder:
            self.scan_single_app(folder)
            
    def auto_scan(self):
        self.status_var.set("Scanning...")
        self.tree.delete(*self.tree.get_children())
        self.apps = []
        
        if not os.path.exists(self.pinokio_path):
            self.status_var.set(f"Path not found: {self.pinokio_path}")
            return
            
        try:
            for item in os.listdir(self.pinokio_path):
                app_path = os.path.join(self.pinokio_path, item)
                if os.path.isdir(app_path):
                    self.scan_app(item, app_path)
                    
            self.status_var.set(f"Found {len(self.apps)} apps")
        except Exception as e:
            self.status_var.set(f"Scan error: {e}")
            
    def scan_single_app(self, app_path):
        app_name = os.path.basename(app_path)
        self.scan_app(app_name, app_path)
        self.status_var.set(f"Added {app_name}")
        
    def scan_app(self, app_name, app_path):
        # Find Python entry points
        entry_points = self.find_python_entries(app_path)
        
        if not entry_points:
            status = "⚠️ No Python"
            entry_text = "None"
            boost_status = False
        else:
            boost_status = self.check_boost_status(entry_points)
            status = "✅ Patched" if boost_status else "❌ Not patched"
            entry_text = ", ".join([os.path.basename(ep) for ep in entry_points])
            
        app_data = {
            'name': app_name,
            'path': app_path,
            'entries': entry_points,
            'boost_status': boost_status,
            'status': status
        }
        
        self.apps.append(app_data)
        
        # Add to tree
        self.tree.insert('', 'end', text=app_name, values=(status, entry_text, app_path))
        
    def find_python_entries(self, app_path):
        """Find potential Python entry points"""
        entry_files = ['main.py', 'app.py', 'webui.py', 'run.py', 'server.py', 'launch.py', 'wgp.py', 'loader.py']
        found_entries = []
        
        for root, dirs, files in os.walk(app_path):
            # Don't go too deep
            depth = root[len(app_path):].count(os.sep)
            if depth >= 3:
                continue
                
            for file in files:
                if file in entry_files:
                    full_path = os.path.join(root, file)
                    found_entries.append(full_path)
                    
        return found_entries
        
    def check_boost_status(self, entry_points):
        """Check if any entry point is already patched"""
        for entry_point in entry_points:
            try:
                with open(entry_point, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(2000)  # Read first 2000 chars
                    if 'AMD-GPU-BOOST' in content or 'apply_boost_optimizations' in content:
                        return True
            except:
                continue
        return False
        
    def patch_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select apps to patch")
            return
            
        success_count = 0
        for item in selected:
            app_name = self.tree.item(item, 'text')
            app_data = next((app for app in self.apps if app['name'] == app_name), None)
            
            if app_data and self.patch_app(app_data):
                success_count += 1
                # Update tree status
                self.tree.item(item, values=("✅ Patched", self.tree.item(item, 'values')[1], self.tree.item(item, 'values')[2]))
                
        messagebox.showinfo("Patching Complete", f"Successfully patched {success_count} apps")
        
    def remove_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select apps to remove patches from")
            return
            
        success_count = 0
        for item in selected:
            app_name = self.tree.item(item, 'text')
            app_data = next((app for app in self.apps if app['name'] == app_name), None)
            
            if app_data and self.remove_patch(app_data):
                success_count += 1
                # Update tree status
                self.tree.item(item, values=("❌ Not patched", self.tree.item(item, 'values')[1], self.tree.item(item, 'values')[2]))
                
        messagebox.showinfo("Removal Complete", f"Successfully removed patches from {success_count} apps")
        
    def patch_app(self, app_data):
        """Patch an app with BOOST"""
        if not app_data['entries']:
            return False
            
        try:
            boost_source = os.path.join(os.path.dirname(__file__), 'boost_v11_plus.py')
            if not os.path.exists(boost_source):
                messagebox.showerror("Error", "boost_v11_plus.py not found!")
                return False
            
            # Patch the main entry point
            main_entry = app_data['entries'][0]  # Use first entry point
            entry_dir = os.path.dirname(main_entry)
            
            # Copy boost_v11_plus.py to the same directory as the entry point
            boost_dest = os.path.join(entry_dir, 'boost_v11_plus.py')
            shutil.copy2(boost_source, boost_dest)
            
            # Create backup
            backup_path = main_entry + '.boost_backup'
            shutil.copy2(main_entry, backup_path)
            
            # Read original content
            with open(main_entry, 'r', encoding='utf-8') as f:
                original_content = f.read()
                
            # Create patched content
            boost_code = '''import os
import logging
import torch
# === AMD-GPU-BOOST INTEGRATION ===
def apply_boost_optimizations():
    """Applies AMD-GPU-BOOST Software-Overclocking for AMD GPUs"""
    boost_logger = logging.getLogger("BOOST_LOADER")
    boost_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    boost_logger.addHandler(handler)
    # === ROCm Check ===
    if torch.version.hip:
        boost_logger.info(f"ROCm detected: {torch.version.hip}")
    else:
        boost_logger.warning("No ROCm backend detected – AMD-GPU-BOOST may not apply")
        return  # Frühzeitig abbrechen, wenn kein ROCm aktiv ist
    try:
        os.environ.setdefault("BOOST_FORCE_MP_COUNT", "72")
        os.environ.setdefault("BOOST_FORCE_WARP_SIZE", "64") 
        os.environ.setdefault("ROCM_PATH", "/opt/rocm-6.4.2")
        os.environ.setdefault("HIP_VISIBLE_DEVICES", "0")
        import boost_v11_plus
        boost_v11_plus.apply_boost_patches()
        boost_logger.info("🚀 AMD-GPU-BOOST activated!")
    except ImportError:
        boost_logger.warning("⚠️ AMD-GPU-BOOST not available")
    except Exception as e:
        boost_logger.warning(f"⚠️ AMD-GPU-BOOST initialization failed: {e}")
# Apply AMD-GPU-BOOST before any GPU operations
apply_boost_optimizations()

'''
            
            # Insert boost code at the beginning (after shebang if present)
            lines = original_content.split('\n')
            insert_pos = 0
            
            # Skip shebang and encoding declarations
            for i, line in enumerate(lines):
                if line.startswith('#!') or line.startswith('# -*- coding'):
                    insert_pos = i + 1
                else:
                    break
                    
            # Insert boost code
            lines.insert(insert_pos, boost_code)
            patched_content = '\n'.join(lines)
            
            # Write patched content
            with open(main_entry, 'w', encoding='utf-8') as f:
                f.write(patched_content)
                
            return True
            
        except Exception as e:
            messagebox.showerror("Patch Error", f"Failed to patch {app_data['name']}: {e}")
            return False
            
    def remove_patch(self, app_data):
        """Remove BOOST patch from an app"""
        if not app_data['entries']:
            return False
            
        try:
            main_entry = app_data['entries'][0]
            entry_dir = os.path.dirname(main_entry)
            backup_path = main_entry + '.boost_backup'
            
            if os.path.exists(backup_path):
                # Restore from backup
                shutil.copy2(backup_path, main_entry)
                os.remove(backup_path)
            else:
                # Remove boost code manually
                with open(main_entry, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Remove boost integration block
                start_marker = "# === AMD-GPU-BOOST INTEGRATION ==="
                end_marker = "apply_boost_optimizations()"
                
                if start_marker in content and end_marker in content:
                    start_pos = content.find(start_marker)
                    end_pos = content.find(end_marker) + len(end_marker) + 1
                    
                    # Remove the boost block
                    new_content = content[:start_pos] + content[end_pos:]
                    
                    with open(main_entry, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                        
            # Remove boost_v11_plus.py from entry directory
            boost_file = os.path.join(entry_dir, 'boost_v11_plus.py')
            if os.path.exists(boost_file):
                os.remove(boost_file)
                
            return True
            
        except Exception as e:
            messagebox.showerror("Remove Error", f"Failed to remove patch from {app_data['name']}: {e}")
            return False
    
    def show_about(self):
        """Show About dialog with project information"""
        about_text = """🚀 AMD-GPU-BOOST Installer v1.0 (for Pinokio)

From 25% to 100% GPU Utilization!

Fixes AMD GPU underperformance in AI/ML applications by correcting PyTorch's ROCm hardware detection at runtime.

Supported GPUs:
• RDNA2: RX 6400 - RX 6950 XT
• RDNA3: RX 7600 - RX 7900 XTX  
• RDNA4: Future support planned

Performance Gains: Up to 4x faster inference!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌟 GitHub: https://github.com/Painter3000/AMD-GPU-BOOST
📧 Issues: Report bugs and request features
💬 Community: Join discussions and share benchmarks

Made with ❤️ for the AMD AI community

MIT License - Free to use, modify, distribute"""

        # Create about window
        about_window = tk.Toplevel(self.root)
        about_window.title("About AMD-GPU-BOOST")
        about_window.geometry("500x400")
        about_window.resizable(False, False)
        
        # Center the window
        about_window.transient(self.root)
        about_window.grab_set()
        
        # Main frame
        frame = ttk.Frame(about_window, padding="20")
        frame.pack(fill='both', expand=True)
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill='both', expand=True)
        
        text_widget = tk.Text(text_frame, wrap='word', font=('Arial', 10), 
                             relief='flat', bg='#f0f0f0', fg='#333333')
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.insert('1.0', about_text)
        text_widget.configure(state='disabled')  # Make read-only
        
        text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Buttons frame
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        # GitHub button
        def open_github():
            import webbrowser
            webbrowser.open("https://github.com/your-repo/amd-gpu-boost")
            
        ttk.Button(button_frame, text="🌟 Visit GitHub", command=open_github).pack(side='left')
        ttk.Button(button_frame, text="Close", command=about_window.destroy).pack(side='right')
            
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = BOOSTInstaller()
    app.run()
