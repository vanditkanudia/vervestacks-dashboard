#!/usr/bin/env python3
"""
Enhanced Branding Manager for VerveStacks
Extends the existing LogoManager with comprehensive branding capabilities
Provides consistent, professional styling across all VERVESTACKS outputs
"""

import os
import yaml
import base64
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.font_manager as fm
from logo_manager import LogoManager


class VerveStacksBrandingManager(LogoManager):
    """
    Enhanced branding manager that extends LogoManager with comprehensive styling
    Provides consistent branding across all chart types and outputs
    """
    
    def __init__(self, config_path="config/branding_config.yaml"):
        """Initialize branding manager with configuration"""
        # Initialize parent LogoManager
        super().__init__()
        
        # Load branding configuration (robust path resolution)
        self.config_path = Path(config_path)
        self.branding_config = self._load_branding_config()
        
        # Set up fonts
        self._setup_fonts()
        
        # Initialize color palettes
        self._initialize_color_palettes()
        
        # ASCII-only to avoid console encoding errors on Windows shells
        print(f"Branding manager initialized. Config: {self.config_path}")
    
    def _load_branding_config(self):
        """Load branding configuration from YAML file with robust path resolution"""
        try:
            module_dir = Path(__file__).parent
            candidate_paths = []

            # 1) If provided path is absolute, try it first
            if self.config_path.is_absolute():
                candidate_paths.append(self.config_path)
            else:
                # 2) CWD-relative (where scripts might run)
                candidate_paths.append(Path.cwd() / self.config_path)
                # 3) Module-relative to this file
                candidate_paths.append(module_dir / self.config_path)
                # 4) Fallback to module_dir/config/branding_config.yaml
                candidate_paths.append(module_dir / 'config' / 'branding_config.yaml')

            for path in candidate_paths:
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f) or {}
                    self.config_path = path
                    # ASCII-only to avoid console encoding errors on Windows
                    print(f"Branding config loaded from: {path}")
                    return config

            print(f"Branding config not found in candidates: {[str(p) for p in candidate_paths]}")
            print("Using default branding settings")
            return self._get_default_config()
        except Exception as e:
            print(f"Error loading branding config: {e}")
            print("Using default branding settings")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Fallback default configuration - now minimal since all values are in config"""
        return {
            'fonts': {'primary': 'DejaVu Sans'},
            'colors': {},
            'chart_styling': {}
        }
    
    def get_font_size(self, size_key):
        """Get font size for a specific key from branding config"""
        try:
            return self.branding_config.get('fonts', {}).get('sizes', {}).get(size_key, 12)
        except Exception:
            return 12  # Default fallback
    
    def _setup_fonts(self):
        """Set up font family with graceful fallback to avoid warnings"""
        try:
            font_family = self.branding_config.get('fonts', {}).get('primary', 'Open Sans')

            # Detect if requested font is available in system
            try:
                import matplotlib.font_manager as _fm
                system_fonts = _fm.findSystemFonts()
                # Check for the actual requested font, not just OpenSans
                font_available = any(font_family.replace(' ', '') in f or font_family in f for f in system_fonts)
            except Exception:
                font_available = False

            if font_available:
                plt.rcParams['font.family'] = [font_family, 'DejaVu Sans', 'sans-serif']
                print(f"Font family set to: {font_family}")
            else:
                # Avoid repeated warnings by not requesting a missing family
                plt.rcParams['font.family'] = ['DejaVu Sans', 'sans-serif']
                print(f"Font '{font_family}' not found. Falling back to DejaVu Sans")
        except Exception as e:
            print(f"⚠️  Font setup error: {e}")
    
    def _initialize_color_palettes(self):
        """Initialize color palettes from configuration"""
        self.colors = self.branding_config.get('colors', {})
        self.gradients = self.colors.get('gradients', {})
        self.neutral_colors = self.colors.get('neutral', {})
    
    def get_color_palette(self, palette_type="primary"):
        """Get color palette for different use cases"""
        if palette_type == "primary":
            return self.colors.get('primary', '#FD275E')
        elif palette_type == "secondary":
            return self.colors.get('secondary', '#FD626B')
        elif palette_type == "accent":
            return self.colors.get('accent', '#FD994C')
        elif palette_type == "primary_gradient":
            return self.gradients.get('primary_scale', ['#FD275E', '#FE5A7A', '#FE8A92'])
        elif palette_type == "coverage":
            return self.gradients.get('coverage', {})
        elif palette_type == "complementary":
            return self.gradients.get('complementary', [])
        else:
            return self.colors.get('primary', '#FD275E')
    
    def format_numbers(self, value):
        """Format numbers with K/M/B notation"""
        try:
            if abs(value) >= 1e9:
                return f"{value/1e9:.1f}B"
            elif abs(value) >= 1e6:
                return f"{value/1e6:.1f}M"
            elif abs(value) >= 1e3:
                return f"{value/1e3:.1f}K"
            else:
                return f"{value:.1f}"
        except:
            return str(value)
    
    def apply_chart_style(self, ax, chart_type="default"):
        """Apply consistent branding to chart axes"""
        try:
            # Get chart styling configuration
            chart_config = self.branding_config.get('chart_styling', {})
            
            # Apply grid styling
            grid_config = chart_config.get('grid_lines', {})
            ax.grid(True, 
                   color=grid_config.get('color', '#E5E5E5'),
                   alpha=grid_config.get('alpha', 0.3),
                   linewidth=grid_config.get('linewidth', 0.5))
            
            # Apply border styling
            border_config = chart_config.get('borders', {})
            for spine in ax.spines.values():
                spine.set_color(border_config.get('color', '#CCCCCC'))
                spine.set_alpha(border_config.get('alpha', 0.5))
                spine.set_linewidth(border_config.get('linewidth', 0.8))
            
            # Apply typography to labels
            self._apply_typography_to_axes(ax)
            
            print(f"Chart style applied for type: {chart_type}")
            
        except Exception as e:
            print(f"⚠️  Error applying chart style: {e}")
    
    def apply_figure_style(self, fig):
        """Apply styling to figure-level elements"""
        try:
            # Apply typography to figure
            self._apply_typography_to_figure(fig)
            
            # Apply title styling for subtle appearance
            self._apply_title_styling(fig)
            
        except Exception as e:
            print(f"⚠️  Error applying figure style: {e}")
    
    def _apply_title_styling(self, fig):
        """Apply subtle title styling based on configuration"""
        try:
            # Get title styling configuration
            header_config = self.branding_config.get('header_band', {})
            title_config = header_config.get('title_styling', {})
            
            # Apply title styling to figure suptitle if it exists
            if hasattr(fig, '_suptitle') and fig._suptitle is not None:
                suptitle = fig._suptitle
                self._style_title_text(suptitle, title_config, "suptitle")
            
            # Check for any text objects that might be titles
            for text_obj in fig.texts:
                if text_obj.get_text() and len(text_obj.get_text()) > 10:  # Likely a title
                    self._style_title_text(text_obj, title_config, "figure_text")
            
        except Exception as e:
            print(f"⚠️  Error applying title styling: {e}")
    
    def _style_title_text(self, text_obj, title_config, text_type):
        """Apply subtle styling to a title text object"""
        try:
            # Validate that text_obj is actually a text object, not a function
            if not hasattr(text_obj, 'set_fontweight') or callable(text_obj):
                print(f"⚠️  Skipping {text_type}: not a valid text object")
                return
                
            # Apply font weight (reduced from bold to normal)
            font_weight = title_config.get('font_weight', 'normal')
            text_obj.set_fontweight(font_weight)
            
            # Apply font size (reduced from 20 to 16)
            font_size = title_config.get('font_size', 16)
            text_obj.set_fontsize(font_size)
            
            # Apply color (changed from bright red to dark gray)
            color = title_config.get('color', '#6C757D')
            text_obj.set_color(color)
            
            # Apply alpha/transparency for subtlety
            alpha = title_config.get('alpha', 0.8)
            text_obj.set_alpha(alpha)
            
            # Apply font family (use configured primary font)
            font_family = title_config.get('font_family', self.branding_config.get('fonts', {}).get('primary', 'DejaVu Sans'))
            text_obj.set_fontfamily(font_family)
            
            print(f"✅ Applied subtle styling to {text_type}: weight={font_weight}, size={font_size}, color={color}, alpha={alpha}")
            
        except Exception as e:
            print(f"⚠️  Error styling {text_type}: {e}")
    
    def create_subtle_title(self, fig, title_text, **kwargs):
        """Create a title with subtle styling applied"""
        try:
            # Get title styling configuration
            header_config = self.branding_config.get('header_band', {})
            title_config = header_config.get('title_styling', {})
            
            # Create suptitle with subtle styling
            suptitle = fig.suptitle(title_text, **kwargs)
            
            # Apply subtle styling
            self._style_title_text(suptitle, title_config, "new_suptitle")
            
            return suptitle
            
        except Exception as e:
            print(f"⚠️  Error creating subtle title: {e}")
            # Fallback to regular suptitle
            return fig.suptitle(title_text, **kwargs)
    
    def finalize_chart_style(self, ax):
        """Apply final typography settings after all chart elements are set"""
        try:
            # Re-apply typography to ensure it's not overridden
            self._apply_typography_to_axes(ax)
            
        except Exception as e:
            print(f"⚠️  Error finalizing chart style: {e}")
    
    def _apply_typography_to_axes(self, ax):
        """Apply typography settings to chart axes"""
        try:
            fonts = self.branding_config.get('fonts', {})
            sizes = fonts.get('sizes', {})
            weights = fonts.get('weights', {})
            
            # Get NEW hierarchical title styling configuration
            header_config = self.branding_config.get('header_band', {})
            title_config = header_config.get('title_styling', {})
            
            # Use chart_title styling for axes titles (professionally visible)
            chart_title_config = title_config.get('chart_title', title_config.get('default', {}))
            title_fontsize = chart_title_config.get('font_size', sizes.get('heading', 12))
            title_fontweight = chart_title_config.get('font_weight', weights.get('heading', 'normal'))
            title_color = chart_title_config.get('color', '#495057')  # Professional dark gray
            title_alpha = chart_title_config.get('alpha', 1.0)  # Full opacity for clarity
            
            # Use existing text styling for labels
            text_color = self.branding_config.get('colors', {}).get('neutral', {}).get('text', '#212529')
            
            # Apply to title using NEW professional chart title styling
            if ax.get_title():
                ax.set_title(ax.get_title(), 
                            fontsize=title_fontsize,
                            fontweight=title_fontweight,
                            color=title_color,
                            alpha=title_alpha)  # Use professional chart title styling
            
            # Apply to x-axis label
            if ax.get_xlabel():
                ax.set_xlabel(ax.get_xlabel(), 
                             fontsize=sizes.get('labels', 5.5),
                             fontweight=weights.get('labels', 'normal'),
                             color=text_color)
            
            # Apply to y-axis label
            if ax.get_ylabel():
                ax.set_ylabel(ax.get_ylabel(), 
                             fontsize=sizes.get('labels', 5.5),
                             fontweight=weights.get('labels', 'normal'),
                             color=text_color)
            
            # Apply to tick labels
            ax.tick_params(axis='both', 
                          labelsize=sizes.get('axis', 7),
                          colors=text_color)
            
        except Exception as e:
            print(f"Error applying typography: {e}")
    
    def _apply_typography_to_figure(self, fig):
        """Apply typography settings to figure-level elements like suptitle"""
        try:
            fonts = self.branding_config.get('fonts', {})
            sizes = fonts.get('sizes', {})
            weights = fonts.get('weights', {})
            
            # Get NEW hierarchical title styling configuration
            header_config = self.branding_config.get('header_band', {})
            title_config = header_config.get('title_styling', {})
            
            # Use main_header styling for figure suptitles (moderately subtle but readable)
            main_header_config = title_config.get('main_header', title_config.get('default', {}))
            title_fontsize = main_header_config.get('font_size', sizes.get('subtitle', 12))
            title_fontweight = main_header_config.get('font_weight', weights.get('subheading', 'normal'))
            title_color = main_header_config.get('color', '#6C757D')  # Professional dark gray
            title_alpha = main_header_config.get('alpha', 0.9)  # High opacity for readability
            
            # Apply to suptitle if it exists using NEW main_header styling
            if hasattr(fig, '_suptitle') and fig._suptitle:
                suptitle_text = fig._suptitle.get_text()
                if suptitle_text:
                    fig.suptitle(suptitle_text, 
                                fontsize=title_fontsize,
                                fontweight=title_fontweight,
                                color=title_color,
                                alpha=title_alpha)  # Use main_header styling
            
        except Exception as e:
            print(f"Error applying typography to figure: {e}")
    
    def add_logos_to_chart(self, fig, logo_size="small", main_title=None):
        """Add both VERVESTACKS and Kanors logos to chart, with header band and optional main title."""
        try:
            header_cfg = self.branding_config.get('header_band', {})
            if header_cfg.get('enabled', True):
                self._add_header_band(fig, header_cfg)
                
                # Add main title in header band if provided
                if main_title:
                    self._add_main_title_in_header(fig, main_title, header_cfg)
            
            logos_config = self.branding_config.get('logos', {})
            if 'vervestacks' in logos_config:
                self._add_single_logo(fig, 'vervestacks', logo_size, 'top_left')
            if 'kanors' in logos_config:
                self._add_single_logo(fig, 'kanors', logo_size, 'top_right')
            print(f"Logos added to chart (size: {logo_size})")
        except Exception as e:
            print(f"Error adding logos: {e}")

    def _add_main_title_in_header(self, fig, title, header_cfg):
        """Add main chart title in the header band."""
        try:
            height_frac = float(header_cfg.get('height_frac', 0.08))
            
            # Get NEW hierarchical title styling configuration
            title_config = header_cfg.get('title_styling', {})
            main_header_config = title_config.get('main_header', title_config.get('default', {}))
            
            # Use main_header styling for header titles (moderately subtle but readable)
            title_color = main_header_config.get('color', '#6C757D')  # Professional dark gray
            title_size = main_header_config.get('font_size', 18)  # Moderately subtle size
            title_weight = main_header_config.get('font_weight', 'normal')  # Normal weight
            title_alpha = main_header_config.get('alpha', 0.9)  # High opacity for readability
            
            # Position title in center of header band
            y_pos = 1.0 - (height_frac / 2)
            fig.text(0.5, y_pos, title, 
                    ha='center', va='center',
                    fontsize=title_size,
                    fontweight=title_weight,
                    color=title_color,
                    alpha=title_alpha,
                    transform=fig.transFigure,
                    zorder=1002)
        except Exception as e:
            print(f"Error adding main title: {e}")
    
    def _add_header_band(self, fig, header_cfg):
        """Draw a header band at top of figure to separate logos/title from plot area."""
        try:
            height_frac = float(header_cfg.get('height_frac', 0.08))
            background_color = header_cfg.get('background', '#F8F9FA')
            divider_color = header_cfg.get('divider_color', '#F0F0F0')
            divider_width = int(header_cfg.get('divider_width', 0.5))
            
            # Full-width rectangle at top with visible background
            rect = patches.Rectangle((0, 1.0 - height_frac), 1.0, height_frac,
                                      transform=fig.transFigure, 
                                      facecolor=background_color, 
                                      edgecolor='none',
                                      zorder=1000)
            fig.patches.append(rect)
            
            # Add divider line at bottom of header band
            divider = patches.Rectangle((0, 1.0 - height_frac), 1.0, divider_width/100,
                                         transform=fig.transFigure,
                                         facecolor=divider_color,
                                         edgecolor='none',
                                         zorder=1001)
            fig.patches.append(divider)

            # Push subplot area down so axes/titles don't get covered by the header band
            spacing = self.branding_config.get('chart_styling', {}).get('spacing', {})
            extra = float(spacing.get('title_margin', 0.05))
            safe_top = max(0.0, 1.0 - height_frac - extra)
            try:
                fig.subplots_adjust(top=safe_top)
            except Exception:
                pass
        except Exception as e:
            print(f"Header band draw error: {e}")

    def _add_single_logo(self, fig, logo_type, size, position):
        """Add a single logo to the chart"""
        try:
            logos_config = self.branding_config.get('logos', {})
            logo_config = logos_config.get(logo_type, {})
            
            # Get logo path and resolve robustly relative to config and repo root
            raw_path = logo_config.get('path', '')
            logo_path = Path(raw_path)
            module_dir = Path(__file__).parent
            candidate_paths = []
            if logo_path.is_absolute():
                candidate_paths.append(logo_path)
            else:
                candidate_paths.append(self.config_path.parent / logo_path)
                candidate_paths.append(module_dir / logo_path)
                candidate_paths.append(Path.cwd() / logo_path)
            resolved = None
            for p in candidate_paths:
                if p.exists():
                    resolved = p
                    break
            if resolved is None:
                print(f"Logo not found. Tried: {[str(p) for p in candidate_paths]}")
                return
            logo_path = resolved
            
            # Get logo size
            size_config = logo_config.get('sizes', {}).get(size, logos_config.get('default_size', [24, 24]))
            
            # Load and process logo
            logo_img = Image.open(logo_path)
            if logo_img.mode != 'RGBA':
                logo_img = logo_img.convert('RGBA')

            # Scale to fixed pixel height
            target_px = int(logos_config.get('target_height_px', 22))
            print(f"   Config target_px: {target_px}")
            w, h = logo_img.size
            if h > 0:
                scale = target_px / float(h)
            else:
                scale = 1.0
            
            print(f"   Logo loaded: {w}x{h}px, scaling to {target_px}px (scale={scale:.3f})")
            
            # Use higher resolution for SVG output with DPI correction
            imagebox = OffsetImage(logo_img, zoom=scale, alpha=0.75, dpi_cor=True)
            
            # If header band enabled, align within it
            header_cfg = self.branding_config.get('header_band', {})
            if header_cfg.get('enabled', False):
                # Position logos within the header band area
                height_frac = float(header_cfg.get('height_frac', 0.08))
                band_top = 1.0
                band_bottom = 1.0 - height_frac
                y = band_top - (height_frac / 2.0)  # Center of header band
                
                if position == 'top_left':
                    x = float(header_cfg.get('left_logo_pos', [0.08, y])[0])
                elif position == 'top_right':
                    x = float(header_cfg.get('right_logo_pos', [0.92, y])[0])
                else:
                    x, y = 0.08, y  # Safe default
            else:
                # Use config-based positioning as fallback
                if position == 'top_left':
                    x = float(header_cfg.get('left_logo_pos', [0.08, 0.96])[0])
                    y = float(header_cfg.get('left_logo_pos', [0.08, 0.96])[1])
                elif position == 'top_right':
                    x = float(header_cfg.get('right_logo_pos', [0.92, 0.96])[0])
                    y = float(header_cfg.get('right_logo_pos', [0.92, 0.96])[1])
                else:
                    x, y = 0.08, 0.96  # Safe default
            
            # Add logo to figure with high zorder to ensure visibility
            # Add padding to prevent cropping
            ab = AnnotationBbox(imagebox, (x, y), 
                              xycoords='figure fraction',
                              frameon=False,
                              pad=0.02)
            ab.set_zorder(1003)  # Higher than header band elements
            
            fig.add_artist(ab)
            
            print(f"✅ Added {logo_type} logo at position ({x:.3f}, {y:.3f}) with size {target_px}px")
            
        except Exception as e:
            print(f"❌ Error adding {logo_type} logo: {e}")
            print(f"   Logo path: {logo_path}")
            print(f"   Position: {position}")
            print(f"   Size: {size}")

    def create_coverage_colormap(self, chart_type="calendar_heatmap"):
        """Create colormap for energy coverage charts"""
        try:
            coverage_colors = self.branding_config.get('colors', {}).get('gradients', {}).get('coverage', {})
            
            if chart_type == "calendar_heatmap":
                # Create teal-based gradient for calendar
                colors_list = [
                    coverage_colors.get('no_data', '#F8F9FA'),  # No data
                    '#e0f2f1',  # Extreme shortage
                    '#b2dfdb',  # Shortage
                    '#80cbc4',  # Moderate shortage
                    '#4db6ac',  # Low coverage
                    '#26a69a',  # Moderate coverage
                    '#00897b',  # Adequate coverage
                    '#00796b',  # Good coverage
                    '#00695c',  # High coverage
                    '#004d40',  # Surplus
                    '#00251a'   # Extreme surplus
                ]
            else:
                # Use brand colors for other chart types
                colors_list = [
                    coverage_colors.get('extreme_shortage', self.colors['primary']),
                    coverage_colors.get('shortage', self.colors['secondary']),
                    coverage_colors.get('moderate', self.colors['accent']),
                    coverage_colors.get('adequate', '#00D8A2'),
                    coverage_colors.get('surplus', '#02A9F4')
                ]
            
            return plt.cm.colors.ListedColormap(colors_list)
            
        except Exception as e:
            print(f"⚠️  Error creating colormap: {e}")
            return plt.cm.viridis  # Fallback
    
    def get_chart_config(self, chart_type):
        """Get specific configuration for chart type"""
        return self.branding_config.get('chart_types', {}).get(chart_type, {})
    
    def print_branding_status(self):
        """Print comprehensive branding status"""
        print(f"🎨 VerveStacksBrandingManager Status:")
        print(f"   Config Path: {self.config_path}")
        print(f"   Config Loaded: {'✅' if self.branding_config else '❌'}")
        print(f"   Primary Color: {self.colors.get('primary', 'N/A')}")
        print(f"   Font Family: {self.branding_config.get('fonts', {}).get('primary', 'N/A')}")
        print(f"   Available Color Palettes: {list(self.gradients.keys())}")
        print(f"   Chart Types: {list(self.branding_config.get('chart_types', {}).keys())}")


# Convenience instance for easy importing
branding_manager = VerveStacksBrandingManager()


# Convenience functions for backward compatibility
def apply_branding_to_chart(ax, chart_type="default"):
    """Apply branding to chart axes"""
    return branding_manager.apply_chart_style(ax, chart_type)


def add_branding_logos(fig, logo_size="small"):
    """Add branding logos to chart"""
    return branding_manager.add_logos_to_chart(fig, logo_size)


def get_brand_colors(palette_type="primary"):
    """Get brand color palette"""
    return branding_manager.get_color_palette(palette_type)


def format_brand_numbers(value):
    """Format numbers with brand styling"""
    return branding_manager.format_numbers(value)


def create_subtle_title(fig, title_text, **kwargs):
    """Create a title with subtle styling applied"""
    return branding_manager.create_subtle_title(fig, title_text, **kwargs)


if __name__ == "__main__":
    # Test the branding manager
    branding_manager.print_branding_status()
