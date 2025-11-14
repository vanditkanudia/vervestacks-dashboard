"""
Logo and Branding Manager for VerveStacks Main Project

Centralized logo and branding management for all VerveStacks outputs.
Provides consistent branding across Excel files, matplotlib plots, and other outputs.
"""

import os
import base64
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox


class LogoManager:
    """Centralized logo and branding management for all VerveStacks outputs"""
    
    # Branding Constants
    BRAND_COLOR = (25, 55, 95)  # Deep blue
    BRAND_TEXT_COLOR = (255, 255, 255)  # White
    
    # Available taglines (for future selection)
    TAGLINES = {
        'main': "VERVESTACKS - the open USE platform · Powered by data · Shaped by vision · Guided by intuition · Fueled by passion",
        'facets': "VERVESTACKS: Energy modeling reimagined · Hourly simulation for any planned mix",
        'grid': "VERVESTACKS: Spatial energy intelligence · Grid-aware modeling at scale",
        'time': "VERVESTACKS: Time dimension intelligence · Algorithmic temporal analysis"
    }
    
    # Default tagline (can be changed)
    DEFAULT_TAGLINE = 'main'
    
    # Logo file path (relative to project root)
    LOGO_FILENAME = "KanorsEMR-Logo-2025_Kanors-Primary-Logo-768x196.webp"
    
    def __init__(self, tagline_key=None):
        """Initialize LogoManager and resolve logo path"""
        self.project_root = Path(__file__).parent
        self.logo_path = self._find_logo_path()
        self.current_tagline = tagline_key or self.DEFAULT_TAGLINE
        
    def _find_logo_path(self):
        """Find the logo file in the project structure"""
        # Try common locations
        possible_paths = [
            self.project_root / "3_model_validation" / self.LOGO_FILENAME,
            self.project_root / self.LOGO_FILENAME,
            self.project_root / "assets" / self.LOGO_FILENAME,
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
                
        # If not found, return the expected path (will be handled gracefully)
        return self.project_root / "3_model_validation" / self.LOGO_FILENAME
    
    def logo_exists(self):
        """Check if logo file exists"""
        return self.logo_path.exists()
    
    @property
    def BRAND_TEXT(self):
        """Get current brand text/tagline"""
        return self.TAGLINES.get(self.current_tagline, self.TAGLINES[self.DEFAULT_TAGLINE])
    
    def set_tagline(self, tagline_key):
        """Set the current tagline"""
        if tagline_key in self.TAGLINES:
            self.current_tagline = tagline_key
            return True
        else:
            print(f"⚠️  Unknown tagline key: {tagline_key}. Available: {list(self.TAGLINES.keys())}")
            return False
    
    def get_available_taglines(self):
        """Get list of available taglines"""
        return {key: tagline for key, tagline in self.TAGLINES.items()}
    
    def get_logo_path(self):
        """Get the absolute path to the logo file"""
        return str(self.logo_path.resolve())
    
    def get_logo_base64(self):
        """Get base64 encoded logo for HTML embedding"""
        try:
            if not self.logo_exists():
                return None
                
            with open(self.logo_path, 'rb') as logo_file:
                logo_data = logo_file.read()
                logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                return logo_base64
                
        except Exception as e:
            print(f"⚠️  Warning: Could not encode logo as base64: {e}")
            return None
    
    def add_matplotlib_watermark(self, fig, alpha=0.4, scale=0.075, position='top-right'):
        """
        Add KanorsEMR logo as watermark to matplotlib figure
        
        Args:
            fig: matplotlib figure object
            alpha: Logo transparency (0-1)
            scale: Logo scale factor
            position: Logo position ('top-right', 'top-left', 'bottom-right', 'bottom-left')
        """
        try:
            # Add tagline to top-left corner
            fig.text(0.02, 0.98, self.BRAND_TEXT, 
                    fontsize=12,
                    color='#2E5984',  # Professional blue color
                    weight='normal',
                    ha='left', va='top',
                    transform=fig.transFigure,
                    alpha=0.8)
            
            if not self.logo_exists():
                print(f"⚠️  Logo file not found: {self.logo_path}")
                return
                
            # Load and process the logo
            logo_img = Image.open(self.logo_path)
            
            # Convert to RGBA if needed
            if logo_img.mode != 'RGBA':
                logo_img = logo_img.convert('RGBA')
            
            # Convert PIL image to numpy array (matplotlib compatible)
            logo_array = np.array(logo_img)
            
            # Create OffsetImage
            imagebox = OffsetImage(logo_array, zoom=scale, alpha=alpha)
            
            # Position mapping
            positions = {
                'top-right': (0.98, 0.98),
                'top-left': (0.02, 0.98),
                'bottom-right': (0.98, 0.02),
                'bottom-left': (0.02, 0.02)
            }
            
            if position not in positions:
                position = 'top-right'
                
            x, y = positions[position]
            
            print(f"   🖼️  Adding logo: {logo_array.shape}, scale={scale}, alpha={alpha}, pos=({x},{y})")
            
            # Add logo to figure
            ab = AnnotationBbox(imagebox, (x, y), 
                              xycoords='figure fraction',
                              frameon=False,
                              pad=0)
            
            # Add to figure (not to specific axes)
            fig.add_artist(ab)
            
            print(f"✅ Logo watermark added to {position}")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not add logo watermark: {e}")
    
    def get_excel_branding_info(self):
        """Get branding information for Excel operations"""
        return {
            'brand_text': self.BRAND_TEXT,
            'brand_color': self.BRAND_COLOR,
            'brand_text_color': self.BRAND_TEXT_COLOR,
            'logo_path': self.get_logo_path() if self.logo_exists() else None
        }
    
    def print_status(self):
        """Print logo manager status for debugging"""
        print(f"🎨 LogoManager Status:")
        print(f"   Project Root: {self.project_root}")
        print(f"   Logo Path: {self.logo_path}")
        print(f"   Logo Exists: {'✅' if self.logo_exists() else '❌'}")
        print(f"   Current Tagline: {self.current_tagline}")
        print(f"   Brand Text: {self.BRAND_TEXT}")
        print(f"   Available Taglines: {list(self.TAGLINES.keys())}")


# Convenience instance for easy importing
logo_manager = LogoManager()


# Convenience functions for backward compatibility
def add_logo_to_plot(fig, **kwargs):
    """Add logo watermark to matplotlib plot"""
    return logo_manager.add_matplotlib_watermark(fig, **kwargs)


def get_logo_path():
    """Get path to logo file"""
    return logo_manager.get_logo_path()


def get_branding_info():
    """Get branding information"""
    return logo_manager.get_excel_branding_info()
