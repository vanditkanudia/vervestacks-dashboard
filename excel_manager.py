"""
Excel Operations Manager

Centralized Excel operations with consistent "Energy Sector" formatting.
Handles all xlwings operations with standardized styling and error handling.
"""

import xlwings as xw
import pandas as pd
import shutil
from pathlib import Path
from contextlib import contextmanager
from logo_manager import logo_manager


class ExcelManager:
    """Manages all Excel operations with consistent formatting and error handling."""
    
    # VerveStacks Branding Constants (now managed by LogoManager)
    @property
    def BRAND_TEXT(self):
        return logo_manager.BRAND_TEXT
    
    @property 
    def BRAND_COLOR(self):
        return logo_manager.BRAND_COLOR
        
    @property
    def BRAND_TEXT_COLOR(self):
        return logo_manager.BRAND_TEXT_COLOR
    
    def __init__(self):
        """Initialize ExcelManager and load sheet documentation."""
        self.sheet_docs = self.load_sheet_documentation()
        self.formatting_mode = self._load_formatting_mode()
        
        print(f"📊 Excel Manager: {self.formatting_mode} formatting mode")
    
    def load_sheet_documentation(self, **flavor_params):
        """
        Load sheet documentation from YAML files with multi-flavor support.
        
        Args:
            **flavor_params: Flavor parameters (e.g., grid_modeling=True)
        
        Returns:
            dict: Combined documentation from base + flavor-specific YAML files
        """
        try:
            # Try different yaml import methods
            try:
                import yaml
            except ImportError:
                try:
                    import ruamel.yaml as yaml
                except ImportError:
                    print("⚠️  No YAML library found. Install with: pip install pyyaml")
                    return {}
            
            from pathlib import Path
            
            # Load base documentation
            base_file = Path("C:/Veda/VerveStacks/config/excel_documentation_base.yaml")
            if not base_file.exists():
                print(f"⚠️  Base documentation file not found: {base_file}")
                return {}
            
            with open(base_file, 'r', encoding='utf-8') as f:
                docs = yaml.safe_load(f) or {}
            
            # Auto-detect and load flavor-specific documentation
            for flavor_name, flavor_enabled in flavor_params.items():
                if flavor_enabled:
                    flavor_file = Path(f"C:/Veda/VerveStacks/config/excel_documentation_{flavor_name}.yaml")
                    if flavor_file.exists():
                        try:
                            with open(flavor_file, 'r', encoding='utf-8') as f:
                                flavor_docs = yaml.safe_load(f) or {}
                            
                            # Merge flavor-specific docs into base docs (flavor overrides base)
                            docs = self._merge_documentation(docs, flavor_docs)
                            print(f"✅ Loaded {flavor_name} flavor documentation")
                        except Exception as e:
                            print(f"⚠️  Could not load {flavor_name} flavor documentation: {e}")
                    else:
                        print(f"ℹ️  No {flavor_name} flavor documentation found at {flavor_file}")
            
            return docs
            
        except Exception as e:
            print(f"⚠️  Could not load sheet documentation: {e}")
            return {}
    
    def _merge_documentation(self, base_docs, flavor_docs):
        """
        Merge flavor-specific documentation into base documentation.
        Flavor docs override/extend base docs.
        """
        import copy
        merged = copy.deepcopy(base_docs)
        
        for workbook_type, sheets in flavor_docs.items():
            if workbook_type not in merged:
                merged[workbook_type] = {}
            
            for sheet_name, sheet_doc in sheets.items():
                if sheet_name not in merged[workbook_type]:
                    merged[workbook_type][sheet_name] = {}
                
                # Merge sheet-level documentation
                for doc_key, doc_value in sheet_doc.items():
                    if doc_key == 'column_documentation':
                        # Special handling for column documentation
                        if 'column_documentation' not in merged[workbook_type][sheet_name]:
                            merged[workbook_type][sheet_name]['column_documentation'] = {}
                        
                        # Merge column docs (flavor overrides base)
                        merged[workbook_type][sheet_name]['column_documentation'].update(doc_value)
                    else:
                        # Direct override for other fields (data_source, methodology_paragraph, purpose_paragraph)
                        merged[workbook_type][sheet_name][doc_key] = doc_value
        
        return merged
    
    def reload_documentation_with_flavors(self, **flavor_params):
        """
        Reload documentation with specific flavor parameters.
        
        Args:
            **flavor_params: Flavor parameters (e.g., grid_modeling=True)
        """
        self.sheet_docs = self.load_sheet_documentation(**flavor_params)
    
    def auto_detect_and_load_flavors(self, **processing_params):
        """
        Auto-detect flavors from processing parameters and reload documentation.
        
        Args:
            **processing_params: Processing parameters that may indicate flavors
                                (e.g., grid_modeling=True, some_other_flavor=True)
        """
        # Extract flavor parameters (boolean flags that indicate flavors)
        flavor_params = {}
        
        # Known flavor mappings
        flavor_mappings = {
            'grid_modeling': 'grid_modeling',
            # Add more flavor mappings as needed
            # 'another_flavor': 'another_flavor',
        }
        
        for param_name, param_value in processing_params.items():
            if param_name in flavor_mappings and param_value:
                flavor_name = flavor_mappings[param_name]
                flavor_params[flavor_name] = True
                print(f"🔧 Detected {flavor_name} flavor from processing parameters")
        
        # Reload documentation with detected flavors
        if flavor_params:
            self.reload_documentation_with_flavors(**flavor_params)
            print(f"✅ Documentation reloaded with flavors: {list(flavor_params.keys())}")
        else:
            print("ℹ️  No flavors detected, using base documentation")
    
    def _load_formatting_mode(self):
        """Load Excel formatting mode from configuration file."""
        try:
            import yaml
            from pathlib import Path
            
            config_path = Path("C:/Veda/VerveStacks/config/excel_formatting.yaml")
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
                
                mode = config.get('formatting', {}).get('mode', 'fast')
                
                if mode not in ['fast', 'full']:
                    print(f"⚠️  Invalid formatting mode '{mode}', defaulting to 'fast'")
                    return 'fast'
                
                return mode
            else:
                # Create default config file
                self._create_default_formatting_config(config_path)
                return 'fast'
                
        except Exception as e:
            print(f"⚠️  Error loading formatting config: {e}, defaulting to 'fast'")
            return 'fast'
    
    def _create_default_formatting_config(self, config_path):
        """Create default formatting configuration file."""
        try:
            import yaml
            from datetime import datetime
            
            default_config = {
                'formatting': {'mode': 'fast'},
                'created': datetime.now().isoformat(),
                'note': 'Auto-created with default fast mode'
            }
            
            config_path.parent.mkdir(exist_ok=True)
            with open(config_path, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False)
            
            print(f"📝 Created default Excel formatting config: {config_path}")
            
        except Exception as e:
            print(f"⚠️  Could not create default config: {e}")
    
    @property
    def is_full_formatting(self):
        """Check if full formatting mode is enabled."""
        return self.formatting_mode == 'full'
    
    @property 
    def is_fast_mode(self):
        """Check if fast mode is enabled."""
        return self.formatting_mode == 'fast'
    
    def add_sheet_documentation(self, worksheet, workbook_type, sheet_name, add_documentation=True):
        """
        Add standardized documentation to any sheet with three-pillar structure.
        
        Args:
            worksheet: xlwings worksheet object
            workbook_type: Type of workbook (e.g., 'vervestacks_ISO', 'scen_par_ngfs')
            sheet_name: Name of the sheet (e.g., 'hourly_resource_shapes')
            add_documentation: If False, only reserves space but doesn't add content
        """
        if workbook_type not in self.sheet_docs or sheet_name not in self.sheet_docs[workbook_type]:
            return
            
        doc = self.sheet_docs[workbook_type][sheet_name]
        
        # Row 1: Branding (handled separately by add_vervestacks_branding)
        # Skip row 1 - it will be handled by add_vervestacks_branding
        
        if add_documentation:
            # ALWAYS: Write content (fast)
            # Row 3: Data Source
            worksheet.range('A3:J3').merge()
            worksheet.range('A3').value = f"Data Source: {doc.get('data_source', '')}"
            
            # Row 4: Methodology
            methodology_text = doc.get('methodology_paragraph', '')
            if methodology_text:
                worksheet.range('A4:J4').merge()
                worksheet.range('A4').value = methodology_text
            
            # Row 5: Purpose
            purpose_text = doc.get('purpose_paragraph', '')
            if purpose_text:
                worksheet.range('A5:J5').merge()
                worksheet.range('A5').value = f"Purpose: {purpose_text}"
            
            # CONDITIONAL: Apply formatting based on YAML config
            if self.is_full_formatting:
                # 🎨 Row 3 formatting
                worksheet.range('A3').font.name = "Segoe UI"
                worksheet.range('A3').font.size = 9
                worksheet.range('A3').font.bold = True
                worksheet.range('A3').font.color = (0, 0, 0)
                worksheet.range('A3').color = (240, 248, 255)
                worksheet.range('A3').api.WrapText = True
                worksheet.range('A3').api.EntireRow.AutoFit()
                
                # 🎨 Row 4 formatting
                if methodology_text:
                    worksheet.range('A4').font.name = "Segoe UI"
                    worksheet.range('A4').font.size = 9
                    worksheet.range('A4').color = (240, 248, 255)
                    worksheet.range('A4').api.WrapText = True
                    worksheet.range('A4').api.VerticalAlignment = -4160
                    worksheet.range('A4').api.EntireRow.AutoFit()
                
                # 🎨 Row 5 formatting
                if purpose_text:
                    worksheet.range('A5').font.name = "Segoe UI"
                    worksheet.range('A5').font.size = 9
                    worksheet.range('A5').font.bold = True
                    worksheet.range('A5').font.color = (0, 0, 0)
                    worksheet.range('A5').color = (240, 248, 255)
                    worksheet.range('A5').api.WrapText = True
                    worksheet.range('A5').api.VerticalAlignment = -4160
                    worksheet.range('A5').api.EntireRow.AutoFit()
        else:
            # Reserve space but don't add content - just set minimal row heights
            worksheet.range('A3').row_height = 15  # Minimal space for row 3
            worksheet.range('A4').row_height = 15  # Minimal space for row 4
            worksheet.range('A5').row_height = 15  # Minimal space for row 5
    
    def add_column_comments(self, worksheet, workbook_type, sheet_name, data_start_row=7, add_comments=True):
        """
        Add rich comments to column headers for contextual documentation.
        
        Args:
            worksheet: xlwings worksheet object
            workbook_type: Type of workbook (e.g., 'vervestacks_ISO')
            sheet_name: Name of the sheet (e.g., 'existing_stock')
            data_start_row: Row where data/headers start (default: 6)
            add_comments: If False, only applies blue styling but no comments
        """
        if (workbook_type not in self.sheet_docs or 
            sheet_name not in self.sheet_docs[workbook_type] or
            'column_documentation' not in self.sheet_docs[workbook_type][sheet_name]):
            return
            
        column_docs = self.sheet_docs[workbook_type][sheet_name]['column_documentation']
        
        # Find the header row (assume it's the first row with data)
        try:
            # Get the used range to find actual column headers
            used_range = worksheet.used_range
            if used_range is None:
                return
                
            # Look for headers starting from data_start_row
            header_row = data_start_row
            header_range = worksheet.range(f'{header_row}:{header_row}')
            
            # Iterate through columns and add comments
            for col_idx, cell in enumerate(header_range, 1):
                if cell.value and str(cell.value).strip():
                    column_name = str(cell.value).strip()
                    
                    if column_name in column_docs:
                        doc = column_docs[column_name]
                        
                        # Create rich comment text with three-pillar structure
                        purpose_text = doc.get('purpose', 'Not specified')
                        comment_text = f"""🎯 PURPOSE: {purpose_text}

💡 DESCRIPTION: {doc.get('description', 'Not specified')}

📊 CALCULATION: {doc.get('calculation', 'Not specified')}

📁 DATA SOURCE: {doc.get('data_source', 'Not specified')}

🔧 METHODOLOGY: {doc.get('methodology', 'Not specified')}

✅ QUALITY: {doc.get('quality_notes', 'Not specified')}

→ See rows 3-5 for complete documentation"""
                        
                        # Add comment and styling based on formatting mode
                        try:
                            # Only add rich comments in full formatting mode
                            add_rich_comments = add_comments and self.is_full_formatting
                            
                            if add_rich_comments:
                                # Use xlwings API to add comment
                                comment = cell.api.AddComment(comment_text)
                                
                                # Auto-size the comment to fit content
                                comment.Shape.TextFrame.AutoSize = True
                            
                            # Style the header cell only in full formatting mode
                            if self.is_full_formatting:
                                cell.font.color = (0, 100, 200)  # Blue text to indicate documentation
                                cell.font.bold = True
                        except Exception as e:
                            print(f"⚠️  Could not add comment to column '{column_name}': {e}")
                            
        except Exception as e:
            print(f"⚠️  Could not add column comments to {sheet_name}: {e}")
    
    @contextmanager
    def workbook(self, file_path, create_new=False):
        """
        Context manager for xlwings workbook operations.
        
        Args:
            file_path: Path to Excel file
            create_new: If True, creates new workbook. If False, opens existing.
        """
        app = xw.App(visible=False)
        app.display_alerts = False
        app.screen_updating = False
        wb = None
        
        try:
            if create_new:
                wb = app.books.add()
            else:
                wb = app.books.open(str(file_path))
            
            yield wb
            
            if wb:
                wb.save(str(file_path))
                wb.close()
                
        except Exception as e:
            if wb:
                try:
                    wb.close()
                except:
                    pass
            raise e
        finally:
            try:
                app.quit()
            except:
                pass
    
    def add_vervestacks_branding(self, worksheet, start_col='A', merge_cols=10, logo_path=None):
        """
        Add VerveStacks branding header to the top row of a worksheet if it's empty.
        
        Args:
            worksheet: xlwings worksheet object
            start_col: Starting column (default 'A')
            merge_cols: Number of columns to merge for branding (default 10)
            logo_path: Optional path to logo image to include in branding band
                      If None, automatically uses LogoManager logo if available
        """
        # Auto-use LogoManager logo if no logo_path specified
        if logo_path is None and logo_manager.logo_exists():
            logo_path = logo_manager.get_logo_path()
        try:
            # Check if row 1 is empty before adding branding
            row1_range = worksheet.range(f"{start_col}1").resize(1, merge_cols)
            existing_values = row1_range.value
            
            # Check if row 1 has any content
            has_content = False
            if existing_values:
                if isinstance(existing_values, list):
                    has_content = any(cell is not None and str(cell).strip() != '' for cell in existing_values)
                else:
                    has_content = existing_values is not None and str(existing_values).strip() != ''
            
            if has_content:
                print("ℹ️  Row 1 contains data - skipping VerveStacks branding")
                return
            
            # Determine layout based on logo presence
            if logo_path and Path(logo_path).exists():
                # Shorten blue band by 2 columns to make space for logo in white area
                blue_band_cols = merge_cols - 2
                
                # Create text branding range (shortened blue band)
                text_range = worksheet.range(f"{start_col}1").resize(1, blue_band_cols)
                text_range.merge()
                text_range.value = self.BRAND_TEXT
                
                # Apply text formatting
                text_range.font.name = "Segoe UI"
                text_range.font.size = 9
                text_range.font.bold = True
                text_range.font.color = self.BRAND_TEXT_COLOR
                text_range.color = self.BRAND_COLOR
                text_range.api.HorizontalAlignment = -4131  # xlLeft
                text_range.api.VerticalAlignment = -4108    # xlVAlignCenter
                
                # Set row height for branding
                worksheet.range(f"{start_col}1").row_height = 22  # Slightly taller for logo
                
                # Add logo image in white space immediately after blue band
                try:
                    # Calculate position immediately after blue band ends
                    logo_col_idx = ord(start_col) - ord('A') + blue_band_cols
                    logo_col = chr(ord('A') + logo_col_idx)
                    logo_cell = worksheet.range(f"{logo_col}1")
                    
                    # Add image with specific sizing - positioned in white space
                    picture = worksheet.pictures.add(
                        logo_path,
                        left=logo_cell.left + 5,  # Small margin from blue band edge
                        top=logo_cell.top + 1,    # Small margin from top
                        height=20,                # Fit within row height
                        width=78                  # Proportional to original 768x196 ratio
                    )
                    
                    print("✅ Logo added in white space after blue band")
                    
                except Exception as logo_error:
                    print(f"⚠️  Warning: Could not add logo in white space: {logo_error}")
                    # If logo fails, just use the shortened blue band
                    pass
                
            else:
                # No logo - use original behavior
                brand_range = worksheet.range(f"{start_col}1").resize(1, merge_cols)
                brand_range.merge()
                brand_range.value = self.BRAND_TEXT
                
                # Apply branding formatting
                brand_range.font.name = "Segoe UI"
                brand_range.font.size = 9
                brand_range.font.bold = True
                brand_range.font.color = self.BRAND_TEXT_COLOR
                brand_range.color = self.BRAND_COLOR
                brand_range.api.HorizontalAlignment = -4131  # xlLeft
                brand_range.api.VerticalAlignment = -4108    # xlVAlignCenter
                
                # Set row height for branding
                worksheet.range(f"{start_col}1").row_height = 20
            
            # Add subtle border to branding area
            try:
                if logo_path and Path(logo_path).exists():
                    # Only border the blue band (shortened)
                    border_range = worksheet.range(f"{start_col}1").resize(1, blue_band_cols)
                else:
                    # Border the full branding area
                    border_range = worksheet.range(f"{start_col}1").resize(1, merge_cols)
                
                border_range.api.Borders.Weight = 2
                border_range.api.Borders.Color = self.BRAND_COLOR
            except:
                pass  # Fallback if border setting fails
                
            print("✅ VerveStacks branding applied to empty row 1")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not apply VerveStacks branding: {e}")
    
    def add_branding_to_workbook(self, file_path):
        """
        Add VerveStacks branding to all sheets in an existing workbook.
        Only adds branding if row 1 is empty on each sheet.
        
        Args:
            file_path: Path to existing Excel file
        """
        try:
            with self.workbook(file_path) as wb:
                for sheet in wb.sheets:
                    print(f"Checking sheet: {sheet.name}")
                    self.add_vervestacks_branding(sheet, start_col='A', merge_cols=12)
                
                wb.app.calculate()  # Refresh formulas
                print("✅ Branding check completed for all sheets")
                
        except Exception as e:
            print(f"Warning: Could not add branding to workbook: {e}")
    
    def apply_smart_number_formatting(self, worksheet, data_range, dataframe):
        """
        Apply intelligent number formatting based on data magnitude.
        Examples: 100., 10.3, 3.02, 0.023, 0.0045
        """
        try:
            # Analyze each column for numeric data
            for col_idx, column_name in enumerate(dataframe.columns):
                col_data = dataframe[column_name]
                
                # Skip non-numeric columns
                if not pd.api.types.is_numeric_dtype(col_data):
                    continue
                
                # Get numeric values (exclude NaN)
                numeric_values = col_data.dropna()
                if numeric_values.empty:
                    continue
                
                # Determine appropriate decimal places based on magnitude
                max_val = abs(numeric_values).max()
                min_val = abs(numeric_values[numeric_values != 0]).min() if any(numeric_values != 0) else 1
                
                # Smart formatting logic
                if max_val >= 100:
                    # Large numbers: 0-1 decimal places
                    if all(numeric_values % 1 == 0):  # All whole numbers
                        format_code = "0."
                    else:
                        format_code = "0.0"
                elif max_val >= 10:
                    # Medium numbers: 1-2 decimal places
                    format_code = "0.0" if min_val >= 1 else "0.00"
                elif max_val >= 1:
                    # Small numbers: 2-3 decimal places
                    format_code = "0.00" if min_val >= 0.1 else "0.000"
                elif max_val >= 0.01:
                    # Very small numbers: 3-4 decimal places
                    format_code = "0.000" if min_val >= 0.001 else "0.0000"
                else:
                    # Tiny numbers: scientific notation or 5 decimal places
                    format_code = "0.00000"
                
                # Apply formatting to the column
                col_range = data_range.offset(0, col_idx).resize(data_range.shape[0], 1)
                col_range.number_format = format_code
                
        except Exception as e:
            # If smart formatting fails, continue without it
            pass
    
    def format_energy_sector_table(self, worksheet, start_cell, data_shape, has_veda_marker=False, marker_offset=(-1, 0), dataframe=None, add_branding=True, logo_path=None):
        """
        Apply Energy Sector formatting based on YAML configuration.
        Fast mode: Essential structure only. Full mode: Complete visual formatting.
        
        Args:
            worksheet: xlwings worksheet
            start_cell: Starting cell (e.g., "B4")
            data_shape: (rows, cols) tuple of data dimensions
            has_veda_marker: If True, formats VEDA marker above table
            marker_offset: Offset for marker position relative to start_cell
            dataframe: pandas DataFrame for smart number formatting (optional)
            add_branding: If True, adds VerveStacks branding to row 1 (default True)
            logo_path: Optional path to logo image for branding band
        """
        num_rows, num_cols = data_shape
        
        # ALWAYS: Essential operations (fast)
        self._write_essential_table_structure(worksheet, start_cell, num_rows, num_cols, 
                                            has_veda_marker, marker_offset, add_branding, logo_path)
        
        # CONDITIONAL: Visual polish based on YAML config
        if self.is_full_formatting:
            self._apply_visual_table_formatting(worksheet, start_cell, num_rows, num_cols, dataframe)

    def _write_essential_table_structure(self, worksheet, start_cell, num_rows, num_cols, 
                                       has_veda_marker, marker_offset, add_branding, logo_path):
        """Fast operations - always executed for table structure."""
        
        # ✅ Basic branding (minimal - just text, no visual formatting)
        if add_branding:
            merge_width = max(num_cols, 10)
            if self.is_full_formatting:
                # Full branding with visual elements
                self.add_vervestacks_branding(worksheet, start_col='A', merge_cols=merge_width, logo_path=logo_path)
            else:
                # Minimal branding - just reserve space
                pass  # Skip branding in fast mode for maximum speed
        
        # ✅ VEDA markers (essential for model functionality)
        if has_veda_marker:
            marker_cell = worksheet.range(start_cell).offset(*marker_offset)
            # Write marker text only, no styling in fast mode
            # Styling will be applied in _apply_visual_table_formatting if full mode
    
    def _apply_visual_table_formatting(self, worksheet, start_cell, num_rows, num_cols, dataframe):
        """Slow operations for visual polish - only in full mode."""
        
        # 🎨 VEDA marker styling
        marker_cell = worksheet.range(start_cell).offset(-1, 0)  # Assume standard offset
        try:
            if marker_cell.value and str(marker_cell.value).startswith('~'):
                marker_cell.font.name = "Consolas"
                marker_cell.font.size = 7
                marker_cell.font.color = (150, 150, 150)
                marker_cell.font.italic = True
        except:
            pass
        
        # 🎨 Header row formatting
        header_range = worksheet.range(start_cell).resize(1, num_cols)
        header_range.font.name = "Segoe UI"
        header_range.font.size = 10
        header_range.font.bold = True
        header_range.font.color = (255, 255, 255)  # White text
        header_range.color = (79, 129, 189)        # Steel blue background
        header_range.api.WrapText = False
        
        # 🎨 Header borders
        try:
            header_range.api.Borders.Weight = 3
        except:
            pass
        
        if num_rows > 1:  # Only format data if there are data rows
            # 🎨 Data rows formatting
            data_range = worksheet.range(start_cell).offset(1, 0).resize(num_rows-1, num_cols)
            data_range.font.name = "Segoe UI"
            data_range.font.size = 9
            data_range.api.WrapText = False
            
            # 🎨 Smart number formatting
            if dataframe is not None:
                self.apply_smart_number_formatting(worksheet, data_range, dataframe)
            
            # 🎨 Alternating row colors
            for i in range(0, num_rows-1, 2):
                try:
                    alt_row = data_range.offset(i, 0).resize(1, num_cols)
                    alt_row.color = (247, 249, 252)  # Very light blue
                except:
                    pass
            
            # 🎨 Data borders
            try:
                data_range.api.Borders.LineStyle = 1
                data_range.api.Borders.Color = (200, 200, 200)
            except:
                pass
        
        # 🎨 Auto-fit columns (expensive operation)
        try:
            for col in range(num_cols):
                col_range = worksheet.range(start_cell).offset(0, col).resize(num_rows, 1)
                col_range.autofit()
                # Set minimum width for readability
                if col_range.column_width < 10:
                    col_range.column_width = 10
                # Set maximum width to prevent excessive stretching
                if col_range.column_width > 30:
                    col_range.column_width = 30
        except:
            pass
    
    def write_formatted_table(self, worksheet, start_cell, dataframe, veda_marker=None, conditional_cell=None):
        """
        Write a dataframe as a formatted table with optional VEDA marker.
        
        Args:
            worksheet: xlwings worksheet
            start_cell: Starting cell for data (e.g., "B4") or special location:
                       "AUTO_ROW10" - automatically finds next available column on row 10 with blank gap
            dataframe: pandas DataFrame to write
            veda_marker: VEDA marker text (e.g., "~tradelinks_dins")
            conditional_cell: Cell reference to check for "x" (e.g., "A11"). If cell contains "x",
                            writes "DeActivated" instead of veda_marker
        """
        # Handle special auto-positioning for row 10
        if start_cell == "AUTO_ROW10":
            start_cell = self._find_next_row10_position(worksheet)
        
        # Write VEDA marker if provided
        if veda_marker:
            marker_cell = worksheet.range(start_cell).offset(-1, 0)
            
            if conditional_cell:
                # Write formula that checks if conditional_cell contains "x"
                formula = f'=IF({conditional_cell}="x","DeActivated","{veda_marker}")'
                marker_cell.value = formula
                print(f"📝 Dynamic marker formula: {formula}")
            else:
                # Write static marker as before
                marker_cell.value = veda_marker
        
        # Write data (headers + rows)
        table_data = [dataframe.columns.tolist()] + dataframe.values.tolist()
        worksheet.range(start_cell).value = table_data
        
        # Apply formatting
        data_shape = (len(table_data), len(dataframe.columns))
        self.format_energy_sector_table(
            worksheet, start_cell, data_shape, 
            has_veda_marker=(veda_marker is not None),
            dataframe=dataframe
        )
    
    def _find_next_row10_position(self, worksheet):
        """
        Find the next available column position on row 10 with a blank column gap.
        
        Row 10 Convention: Data tables are placed on row 10 with blank columns between them.
        Rows 1-9 are reserved for documentation, headers, and metadata.
        
        Args:
            worksheet: xlwings worksheet
            
        Returns:
            str: Cell reference for next position (e.g., "Q10")
        """
        try:
            # Find last used column on row 10
            used_range = worksheet.used_range
            if used_range and used_range.last_cell.row >= 10:
                # Check each column on row 10 to find the last non-empty one
                last_col = 1
                for col in range(1, used_range.last_cell.column + 1):
                    cell_value = worksheet.range(10, col).value
                    if cell_value is not None and str(cell_value).strip():
                        last_col = col
                
                # Place new data 2 columns after (1 blank column gap)
                next_col = last_col + 2
            else:
                # Fallback if no data on row 10 yet
                next_col = 2  # Column B
            
            # Convert column number to Excel letter format (handles AA, AB, etc.)
            def col_num_to_letter(col_num):
                result = ""
                while col_num > 0:
                    col_num -= 1
                    result = chr(65 + col_num % 26) + result
                    col_num //= 26
                return result
            
            return f"{col_num_to_letter(next_col)}10"
            
        except Exception as e:
            # Fallback to a safe position if detection fails
            return "Q10"
    
    def write_grid_trade_links(self, dest_folder, grid_data):
        """Write grid trade links to Excel file with Energy Sector formatting."""
        try:
            # Create trades folder
            trades_folder = dest_folder / "suppxls" / "trades"
            trades_folder.mkdir(parents=True, exist_ok=True)
            
            trade_links_file = trades_folder / "scentrade__trade_links.xlsx"
            
            with self.workbook(trade_links_file, create_new=True) as wb:
                # Create grid_links sheet
                ws = wb.sheets[0]
                ws.name = "grid_links"
                
                # Write TradeLinks_DINS table starting at B4
                dins_data = grid_data['grid_links_DINS']
                self.write_formatted_table(ws, "B4", dins_data, "~tradelinks_dins")
                
                # Calculate position for second table (side by side with 2 empty columns)
                dins_cols = len(dins_data.columns)
                desc_start_col = chr(ord('B') + dins_cols + 2)
                
                # Write TradeLinks_Desc table side by side
                desc_data = grid_data['grid_links_Desc']
                self.write_formatted_table(ws, f"{desc_start_col}4", desc_data, "~tradelinks_desc")
            
            print(f"✅ Grid trade links written to: {trade_links_file}")
            
        except Exception as e:
            print(f"Warning: Failed to write grid trade links: {e}")
    
    def get_international_trade_buses(self, input_iso, data_source=None):
        """
        Returns a list of bus_ids (converted to commodity format) for buses that have 
        at least one line connected to buses in other ISOs.
        
        Args:
            input_iso (str): ISO code (e.g., 'CHE', 'DEU', 'FRA')
            
        Returns:
            list: List of bus_ids converted to commodity format with prefix
        """
        import pandas as pd
        from pathlib import Path
        from shared_data_loader import get_shared_loader
        from spatial_utils import bus_id_to_commodity
        
        # Define paths to the raw OSM data
        script_dir = Path(__file__).resolve().parent
        # if data_source == 'eur':
        #     buses_file = script_dir / "data" / "OSM-Eur-prebuilt" / "buses.csv"
        #     lines_file = script_dir / "data" / "OSM-Eur-prebuilt" / "lines.csv"
        # else:
        #     buses_file = script_dir / "data" / "OSM-kan-prebuilt" / "buses.csv"
        #     lines_file = script_dir / "data" / "OSM-kan-prebuilt" / "lines.csv"

        buses_file = script_dir / "data" / "OSM-Eur-prebuilt" / "buses.csv"
        lines_file = script_dir / "data" / "OSM-Eur-prebuilt" / "lines.csv"

        
        # Check if files exist
        if not buses_file.exists() or not lines_file.exists():
            print(f"⚠️  Grid data files not found - skipping international trade buses")
            return []
        
        try:
            # Load region mapping from VS mappings
            shared_loader = get_shared_loader("data/")
            region_map = shared_loader.get_region_map()
            
            # Create ISO3 to ISO2 mapping from region map
            iso3_to_iso2_map = dict(zip(region_map['iso'], region_map['2-alpha code']))
            target_iso2 = iso3_to_iso2_map.get(input_iso)
            
            if not target_iso2:
                print(f"⚠️  Unknown ISO code: {input_iso} - skipping international trade buses")
                return []
            
            # Load the raw grid data (suppress dtype warning)
            buses_df = pd.read_csv(buses_file)
            lines_df = pd.read_csv(lines_file, low_memory=False)
            
            # Create bus-to-country mapping
            bus_country_map = dict(zip(buses_df['bus_id'], buses_df['country']))
            
            # Add country information to lines
            lines_df['bus0_country'] = lines_df['bus0'].map(bus_country_map)
            lines_df['bus1_country'] = lines_df['bus1'].map(bus_country_map)
            
            # Remove lines where country information is missing
            lines_df = lines_df.dropna(subset=['bus0_country', 'bus1_country'])
            
            # Find cross-border lines
            cross_border_lines = lines_df[
                lines_df['bus0_country'] != lines_df['bus1_country']
            ].copy()
            
            if cross_border_lines.empty:
                return []
            
            # Get buses from the target country that participate in international trade
            target_bus_ids = set()
            
            # Check bus0 connections (target country bus connecting to foreign bus)
            target_bus0_connections = cross_border_lines[
                cross_border_lines['bus0_country'] == target_iso2
            ]

            target_bus_ids.update(target_bus0_connections['bus0'].tolist())
            
            # Check bus1 connections (foreign bus connecting to target country bus)  
            target_bus1_connections = cross_border_lines[
                cross_border_lines['bus1_country'] == target_iso2
            ]

            target_bus_ids.update(target_bus1_connections['bus1'].tolist())

           # NEW: If synthetic grid, map OSM buses to demand clusters
            if data_source and data_source.startswith('syn'):
                # Get coordinates for OSM trade buses
                trade_buses_df = buses_df[buses_df['bus_id'].isin(target_bus_ids)].copy()
                
                # Load synthetic demand clusters
                syn_buses_path = script_dir / f"1_grids/output_{data_source}/{input_iso}/{input_iso}_clustered_buses.csv"
                
                if not syn_buses_path.exists():
                    print(f"⚠️  Synthetic buses not found at {syn_buses_path} - skipping international trade")
                    return []
                
                syn_buses = pd.read_csv(syn_buses_path)
                demand_clusters = syn_buses[syn_buses['bus_id'].str.startswith('dem')].copy()
                
                if demand_clusters.empty:
                    print(f"⚠️  No demand clusters found - skipping international trade")
                    return []
                
                # Map each OSM trade bus to nearest demand cluster using BallTree
                from sklearn.neighbors import BallTree
                import numpy as np
                
                demand_coords_rad = np.radians(demand_clusters[['y', 'x']].values)  # lat, lon
                osm_coords_rad = np.radians(trade_buses_df[['y', 'x']].values)
                
                tree = BallTree(demand_coords_rad, metric='haversine')
                distances, indices = tree.query(osm_coords_rad, k=1)
                
                # Get unique demand clusters that map to trade buses
                target_bus_ids = demand_clusters.iloc[indices.flatten()]['bus_id'].unique()
                
                print(f"  ✓ Mapped {len(trade_buses_df)} OSM trade buses to {len(target_bus_ids)} demand clusters") 
            
            # Convert bus_ids to commodity format using the existing function
            commodity_bus_ids = [bus_id_to_commodity(bus_id, add_prefix=True) for bus_id in target_bus_ids]
            
            return sorted(commodity_bus_ids)
            
        except Exception as e:
            print(f"⚠️  Error getting international trade buses: {e}")
            return []

    def write_grid_capacity_to_base_vs(self, base_vs_path, grid_data, input_iso=None, data_source=None):
        """Write grid capacity data to Base VS file with Energy Sector formatting."""
        try:
            import pandas as pd
            with self.workbook(base_vs_path) as wb:
                # Add or get grids sheet
                try:
                    ws = wb.sheets["grids"]
                    ws.clear()  # Clear existing content
                except:
                    ws = wb.sheets.add("grids")
                
                # Write grid capacity table with smart formatting
                pasti_data = grid_data['grids_parameters']
                self.write_formatted_table(ws, "B3", pasti_data, "~TFM_INS-AT")

                self.write_formatted_table(ws, "H3", grid_data['df_demtech_flo_mark'], "~tfm_ins-at")
                self.write_formatted_table(ws, "P3", grid_data['df_demtech_topins'], "~tfm_topins")                

                # Write topology data if available
                topology_data = grid_data.get('topology_data')
                if topology_data is not None and not topology_data.empty:
                    self.write_formatted_table(ws, "U3", topology_data, "~tfm_topins")
                    print(f"✅ Topology data written to Base VS file: {len(topology_data)} entries")
                else:
                    print(f"⚠️  No topology data to write to Base VS file")
                
                # disable production of ELC in grid modeling
                ws.range('AA3').value = '~tfm_ins-at'
                ws.range('AA4').value = 'commodity'
                ws.range('AA5').value = 'ELC'
                ws.range('AA6').value = 'ELC'
                ws.range('AB4').value = 'limtype'
                ws.range('AB5').value = 'UP'
                ws.range('AB6').value = 'UP'
                ws.range('AC4').value = 'flo_bnd'
                ws.range('AD4').value = 'stgout_bnd'
                ws.range('AC5').value = 2
                ws.range('AD6').value = 2
                ws.range('AE4').value = 'year'
                ws.range('AE5').value = '0'
                ws.range('AE6').value = '0'
                ws.range('AF4').value = 'pset_set'
                ws.range('AF5').value = 'ELE,DMD,PRE'
                ws.range('AF6').value = 'STG'

                # Write international trade table if input_iso is provided
                trade_buses = self.get_international_trade_buses(input_iso, data_source=data_source)
                if trade_buses:
                    # Create the commodity list (same for both import and export)
                    commodity_list = ','.join(trade_buses)
                    
                    # Create DataFrame for international trade processes
                    trade_df = pd.DataFrame({
                        'process': ['Trd_electricity import', 'Trd_electricity export'],
                        'commodity': [commodity_list, commodity_list],
                        'io': ['OUT', 'IN']
                    })
                    
                    # Find the rightmost used column and add gap
                    used_range = ws.used_range
                    if used_range:
                        last_col = used_range.last_cell.column + 2  # One column gap
                    else:
                        last_col = 1
                    
                    # Convert column number to letter for cell reference
                    def col_num_to_letter(col_num):
                        result = ""
                        while col_num > 0:
                            col_num -= 1
                            result = chr(col_num % 26 + ord('A')) + result
                            col_num //= 26
                        return result
                    
                    start_cell = f"{col_num_to_letter(last_col)}3"
                    
                    # Use the standard formatted table writer
                    self.write_formatted_table(ws, start_cell, trade_df, "~tfm_topins")
                    
                    print(f"✅ International trade table written to Base VS file: {len(trade_buses)} buses, 2 processes")
                else:
                    print(f"⚠️  No international trade buses found for {input_iso}")

            print(f"✅ Grid capacity table written to Base VS file")
            
        except Exception as e:
            print(f"Warning: Could not write grid capacity table: {e}")
    
    def write_grid_transformers_sheet(self, wb, iso3_code, data_source="kan"):
        """
        Analyze transformer substations and create grid_transformers sheet.
        
        Reads clustered buses data and creates step-down transformer processes
        for multi-voltage substations (same tag, different voltages).
        
        Args:
            wb: xlwings workbook object
            iso3_code: ISO3 country code for file paths
            data_source: Data source directory ('kan' or 'cit')
        """
        try:
            from spatial_utils import bus_id_to_commodity
            
            # Read clustered buses data
            buses_file = Path(f"1_grids/output_{data_source}/{iso3_code}/{iso3_code}_clustered_buses.csv")
            
            if not buses_file.exists():
                print(f"⚠️  Grid transformers: Clustered buses file not found for {iso3_code}")
                return
            
            buses_df = pd.read_csv(buses_file)
            
            # Find tags with more than one row (multi-voltage substations)
            tag_counts = buses_df['tags'].value_counts()
            multi_tag = tag_counts[tag_counts > 1].index
            
            if len(multi_tag) == 0:
                print(f"⚠️  Grid transformers: No multi-voltage substations found for {iso3_code}")
                return
            
            # Filter to only those tags
            df_multi = buses_df[buses_df['tags'].isin(multi_tag)].copy()
            
            # Sort by tag and voltage descending (convert voltage to numeric for sorting)
            df_multi['voltage_num'] = pd.to_numeric(df_multi['voltage'], errors='coerce')
            df_multi = df_multi.sort_values(['tags', 'voltage_num'], ascending=[True, False])
            
            # For each tag, create step-down transformer records
            stepdown_records = []
            for tag, group in df_multi.groupby('tags'):
                group_sorted = group.sort_values('voltage_num', ascending=False)
                bus_ids = group_sorted['bus_id'].tolist()
                voltages = group_sorted['voltage_num'].tolist()
                for i in range(len(bus_ids) - 1):
                    higher_bus = bus_ids[i]
                    lower_bus = bus_ids[i+1]
                    higher_v = voltages[i]
                    lower_v = voltages[i+1]
                    # Pass bus ids through bus_id_to_commodity
                    comm_in = bus_id_to_commodity(higher_bus, add_prefix=True)
                    comm_out = bus_id_to_commodity(lower_bus, add_prefix=True)
                    stepdown_records.append({
                        'process': f"stepdown_{bus_id_to_commodity(tag, add_prefix=False)}_{int(higher_v)}to{int(lower_v)}",
                        'comm-in': comm_in,
                        'comm-out': comm_out,
                        'efficiency': 1
                    })

                    stepdown_records.append({
                        'process': f"stepup_{bus_id_to_commodity(tag, add_prefix=False)}_{int(lower_v)}to{int(higher_v)}",
                        'comm-in': comm_out,
                        'comm-out': comm_in,
                        'efficiency': 1
                    })
            
            if not stepdown_records:
                print(f"⚠️  Grid transformers: No transformer connections found for {iso3_code}")
                return
            
            df_stepdown = pd.DataFrame(stepdown_records)
            
            # Create process descriptions table
            df_stepdown_desc = pd.DataFrame({
                'set': "pre",
                'process': df_stepdown['process'],
                'description': (
                    "Transformer: "
                    + df_stepdown['comm-in'] + " → " + df_stepdown['comm-out']
                ),
                'activityunit': "TWh",
                'capacityunit': "GW",
                'timeslicelevel': "daynite"
            })
            
            # Create or get grid_transformers sheet
            if "grid_transformers" in [s.name for s in wb.sheets]:
                ws = wb.sheets["grid_transformers"]
            else:
                ws = wb.sheets.add("grid_transformers", after=wb.sheets[-1])
            
            # Write first table (stepdown transformers) starting at B3
            self.write_formatted_table(ws, "B3", df_stepdown, "~fi_t")
            
            # Calculate position for second table (one column after first table ends)
            first_table_end_col = len(df_stepdown.columns) + 1  # B=1, so +len gives next column after table
            second_table_start_col = first_table_end_col + 2  # +1 for blank column, +1 for next column
            second_table_cell = f"{chr(65 + second_table_start_col)}3"  # Convert to Excel column letter
            
            # Write second table (descriptions) 
            self.write_formatted_table(ws, second_table_cell, df_stepdown_desc, "~fi_process")
            
            print(f"✅ Grid transformers: Added {len(df_stepdown)} transformer processes to SubRES")
            
        except Exception as e:
            print(f"⚠️  Grid transformers: Could not process transformers for {iso3_code}: {e}")
    
    def write_re_subres_data(self, subres_file_path, solar_wind_data=None, input_iso=None, iso_processor=None):
        """Update SubRES file with renewable energy potential data using Energy Sector formatting."""
        try:
            with self.workbook(subres_file_path) as wb:
                # # Hydro
                # if "hydro" in [s.name for s in wb.sheets]:
                #     ws = wb.sheets["hydro"]
                # else:
                #     ws = wb.sheets.add("hydro", after=wb.sheets[-1])
                
                # # Write process data starting at B3
                # self.write_formatted_table(ws, "AUTO_ROW10", process_df, "~fi_process")
                
                # # Write fi_t data starting at I3 (side by side)
                # self.write_formatted_table(ws, "AUTO_ROW10", fi_t_df, "~fi_t")
            
                # Solar and Wind data (only if provided)
                if solar_wind_data is not None:
                    # Solar
                    if "solar" in [s.name for s in wb.sheets]:
                        ws = wb.sheets["solar"]
                    else:
                        ws = wb.sheets.add("solar", after=wb.sheets[-1])
                    
                    # Write solar process data starting at B3 (only if not empty)
                    if not solar_wind_data['df_solar_fi_p'].empty:
                        self.write_formatted_table(ws, "AUTO_ROW10", solar_wind_data['df_solar_fi_p'], "~fi_process")
                        self.write_formatted_table(ws, "AUTO_ROW10", solar_wind_data['df_solar_fi_t'], "~fi_t")
                    
                    # Check if grid_modeling is active in the solar_wind_data dict (passed from upstream)
                    if iso_processor.grid_modeling:
                        if not solar_wind_data['df_agg_sol_fi_p'].empty:
                            self.write_formatted_table(ws, "AUTO_ROW10", solar_wind_data['df_agg_sol_fi_p'], "~fi_process")

                            self.write_formatted_table(ws, "AUTO_ROW10", solar_wind_data['df_agg_sol_fi_t'], "~fi_t")

                        if not solar_wind_data['df_agg_won_fi_p'].empty:
                            self.write_formatted_table(ws, "AUTO_ROW10", solar_wind_data['df_agg_won_fi_p'], "~fi_process")
                            self.write_formatted_table(ws, "AUTO_ROW10", solar_wind_data['df_agg_won_fi_t'], "~fi_t")

                        if not solar_wind_data['df_agg_wof_fi_p'].empty:
                            self.write_formatted_table(ws, "AUTO_ROW10", solar_wind_data['df_agg_wof_fi_p'], "~fi_process")
                            self.write_formatted_table(ws, "AUTO_ROW10", solar_wind_data['df_agg_wof_fi_t'], "~fi_t")

                    # Wind
                    if "wind" in [s.name for s in wb.sheets]:
                        ws = wb.sheets["wind"]
                    else:
                        ws = wb.sheets.add("wind", after=wb.sheets[-1])

                    # Write wind onshore process data starting at AUTO_ROW10 (only if not empty)
                    if not solar_wind_data['df_won_fi_p'].empty:
                        self.write_formatted_table(ws, "AUTO_ROW10", solar_wind_data['df_won_fi_p'], "~fi_process")

                    # Write wind onshore fi_t data starting at I3 (side by side)
                        self.write_formatted_table(ws, "AUTO_ROW10", solar_wind_data['df_won_fi_t'], "~fi_t")


                    # Write wind offshore process data starting at B3 (only if not empty)
                    if not solar_wind_data['df_wof_fi_p'].empty:
                        self.write_formatted_table(ws, "AUTO_ROW10", solar_wind_data['df_wof_fi_p'], "~fi_process")

                    # Write wind offshore fi_t data starting at I3 (side by side)
                        self.write_formatted_table(ws, "AUTO_ROW10", solar_wind_data['df_wof_fi_t'], "~fi_t")

                # WEO Conventional Technologies data
                # Get ISO code from parameter or extract from path
                try:
                    iso_code = input_iso
                    
                    # Construct path to VerveStacks file in output folder
                    # Path structure: output/VerveStacks_ISO.xlsx
                    vervestacks_file = Path("output") / f"VerveStacks_{iso_code}.xlsx"
                    
                    if vervestacks_file.exists():
                        import duckdb
                        weo_pg_df = pd.read_excel(vervestacks_file, sheet_name="weo_pg", skiprows=2, usecols=lambda x: x != 'Unnamed: 0')
                        
                        # Register the DataFrame for SQL queries
                        duckdb.register('weo_pg_df', weo_pg_df)
                        
                        # Create fi_t_weo (technology parameters)
                        fi_t_weo = duckdb.sql("""
                            select T1.technology AS process,T1.model_fuel AS "comm-in",'ELC' as "comm-out",
                            "2023","2030","2050",
                            T1.model_attribute AS attribute
                            from weo_pg_df T1
                            where T1.scenario ilike 'Stated%'
                            order by T1.technology,T1.model_attribute
                        """).df()
                        
                        # Create fi_p_weo (process definitions)
                        fi_p_weo = duckdb.sql("""
                            select 
                            'ele' AS set,
                            T1.technology AS process,'' AS description,
                            'GW' AS capacity_unit,
                            'TWh' AS activity_unit,
                            'daynite' AS timeslicelevel,
                            'yes' AS vintage
                            from weo_pg_df T1
                            group by T1.technology
                            order by T1.technology
                        """).df()
                        
                        # Create or get conventional technologies sheet
                        if "conventional" in [s.name for s in wb.sheets]:
                            ws = wb.sheets["conventional"]
                        else:
                            ws = wb.sheets.add("conventional", after=wb.sheets[-1])
                        
                        # Write WEO technology parameters (fi_t)
                        self.write_formatted_table(ws, "AUTO_ROW10", fi_t_weo, "~fi_t")
                        
                        # Write WEO process definitions (fi_process) side by side
                        self.write_formatted_table(ws, "AUTO_ROW10", fi_p_weo, "~fi_process")
                        
                        print(f"✅ WEO conventional technologies (fi_t and fi_process) added to SubRES")
                    else:
                        print(f"Warning: VerveStacks file not found at {vervestacks_file}")
                        
                except Exception as e:
                    print(f"Warning: Could not add WEO conventional technologies: {e}")
                
                # Grid Transformers (only when grid modeling is active)
                if input_iso and iso_processor and iso_processor.grid_modeling:
                    self.write_grid_transformers_sheet(wb, input_iso, iso_processor.data_source)
            
            print(f"✅ SubRES renewable data updated successfully")
            
        except Exception as e:
            print(f"Warning: Could not update SubRES renewable data: {e}")
            print(f"SubRES file path: {subres_file_path}")
            print(f"File exists: {Path(subres_file_path).exists() if subres_file_path else 'N/A'}")
    

    def update_system_settings_with_grids(self, syssettings_path, input_iso, commodities_df, grid_data=None):
        """Update system settings with ISO code and grid data using Energy Sector formatting."""
        try:
            with self.workbook(syssettings_path) as wb:
                # Update ISO code
                ws_sys = wb.sheets["system_settings"]
                ws_sys.range("B3").value = input_iso
                
                # Write SubRES commodities on fuels sheet
                ws_fuels = wb.sheets["fuels"]
                ws_fuels.range("M4").options(index=False).value = commodities_df
                
                # Write grid commodities if available
                if grid_data:
                    fi_comm_grids = grid_data.get('fi_comm_grids')
                    if fi_comm_grids is not None:
                        try:
                            ws_grids = wb.sheets["grids"]
                            ws_grids.clear()
                        except:
                            ws_grids = wb.sheets.add("grids")
                        
                        # Write with Energy Sector formatting and smart number formatting
                        self.write_formatted_table(ws_grids, "B4", fi_comm_grids, "~fi_comm")
                
                # Refresh formulas
                wb.app.calculate()
            
            return True
            
        except Exception as e:
            print(f"Warning: Excel operations failed: {e}")
            return False

    def create_historical_data_sheet(self, output_path, df_ember_util, df_irena_util, iso_processor):
        """
        Create professional historical_data sheet with Energy Sector formatting.
        
        Args:
            output_path: Path to the VerveStacks Excel file
            df_ember_util: EMBER utilization data DataFrame
            df_irena_util: IRENA utilization data DataFrame  
            iso_processor: ISO processor object with main data
        """
        try:
            with self.workbook(output_path) as wb:
                # Create or clear historical_data sheet
                if 'historical_data' in [ws.name for ws in wb.sheets]:
                    ws = wb.sheets['historical_data']
                    ws.clear()
                else:
                    ws = wb.sheets.add('historical_data')
                
                current_row = 3  # Start after branding row and buffer
                iso = iso_processor.input_iso
                
                # --- EMBER Capacity & Generation ---
                df_ember = iso_processor.main.df_ember
                
                # Generation (TWh)
                df_generation = df_ember[(df_ember['Unit'] == 'TWh') & (df_ember['iso_code'] == iso)].copy()
                if not df_generation.empty:
                    
                    df_historical_long = df_generation.copy()

                    gen_pivot = df_generation.pivot_table(
                        index=['model_fuel'], columns='Year', values='Value', aggfunc='sum'
                    ).reset_index()
                    
                    ws.range(f'A{current_row-1}').value = "EMBER Generation (TWh)"
                    ws.range(f'A{current_row}').value = [gen_pivot.columns.tolist()] + gen_pivot.values.tolist()
                    
                    data_shape = (len(gen_pivot) + 1, len(gen_pivot.columns))
                    self.format_energy_sector_table(ws, f'A{current_row}', data_shape, 
                                                   has_veda_marker=True, marker_offset=(-1, 0), dataframe=gen_pivot, add_branding=False)
                    
                    current_row += len(gen_pivot) + 3
                
                # Capacity (GW)
                df_capacity = df_ember[(df_ember['Unit'] == 'GW') & (df_ember['iso_code'] == iso)].copy()
                if not df_capacity.empty:

                    df_historical_long = pd.concat([df_historical_long, df_capacity])
                    
                    cap_pivot = df_capacity.pivot_table(
                        index=['model_fuel'], columns='Year', values='Value', aggfunc='sum'
                    ).reset_index()
                    
                    ws.range(f'A{current_row-1}').value = "EMBER Capacity (GW)"
                    ws.range(f'A{current_row}').value = [cap_pivot.columns.tolist()] + cap_pivot.values.tolist()
                    
                    data_shape = (len(cap_pivot) + 1, len(cap_pivot.columns))
                    self.format_energy_sector_table(ws, f'A{current_row}', data_shape, 
                                                   has_veda_marker=True, marker_offset=(-1, 0), dataframe=cap_pivot, add_branding=False)
                    
                    current_row += len(cap_pivot) + 3

                # delete model_fuel = solar/windon/windoff from df_historical_long so that it can be replaced by IRENA data
                df_historical_long = df_historical_long[df_historical_long['model_fuel'] != 'solar']
                df_historical_long = df_historical_long[df_historical_long['model_fuel'] != 'windon']
                df_historical_long = df_historical_long[df_historical_long['model_fuel'] != 'windoff']

                # Emissions (Mt CO2)
                df_emissions = df_ember[(df_ember['Unit'] == 'mtCO2') & (df_ember['iso_code'] == iso)].copy()
                if not df_emissions.empty:
                    
                    df_historical_long = pd.concat([df_historical_long, df_emissions])

                    emissions_pivot = df_emissions.pivot_table(
                        index=['model_fuel'], columns='Year', values='Value', aggfunc='sum'
                    ).reset_index()
                    
                    ws.range(f'A{current_row-1}').value = "EMBER Emissions (Mt CO2)"
                    ws.range(f'A{current_row}').value = [emissions_pivot.columns.tolist()] + emissions_pivot.values.tolist()
                    
                    data_shape = (len(emissions_pivot) + 1, len(emissions_pivot.columns))
                    self.format_energy_sector_table(ws, f'A{current_row}', data_shape, 
                                                   has_veda_marker=True, marker_offset=(-1, 0), dataframe=cap_pivot, add_branding=False)
                    
                    current_row += len(cap_pivot) + 3

                # --- IRENA Capacity & Generation (if available) ---
                if iso_processor.main.df_irena_c is not None and iso_processor.main.df_irena_g is not None:
                    # IRENA Generation (TWh)
                    df_irena_gen_iso = iso_processor.main.df_irena_g[iso_processor.main.df_irena_g['iso_code'] == iso].copy()
                    if not df_irena_gen_iso.empty:
                        irena_gen_pivot = df_irena_gen_iso.pivot_table(
                            index=['model_fuel'], columns='Year', values='Electricity statistics (MW/GWh)', aggfunc='sum'
                        ).reset_index()
                        
                        # Convert GWh to TWh
                        import numpy as np
                        numeric_cols = irena_gen_pivot.select_dtypes(include=[np.number]).columns
                        irena_gen_pivot[numeric_cols] = irena_gen_pivot[numeric_cols] / 1000
                        
                        ws.range(f'A{current_row-1}').value = "IRENA Generation (TWh)"
                        ws.range(f'A{current_row}').value = [irena_gen_pivot.columns.tolist()] + irena_gen_pivot.values.tolist()
                        
                        data_shape = (len(irena_gen_pivot) + 1, len(irena_gen_pivot.columns))
                        self.format_energy_sector_table(ws, f'A{current_row}', data_shape, 
                                                       has_veda_marker=True, marker_offset=(-1, 0), dataframe=irena_gen_pivot, add_branding=False)
                        
                        current_row += len(irena_gen_pivot) + 3
                    
                    # IRENA Capacity (GW)
                    df_irena_cap_iso = iso_processor.main.df_irena_c[iso_processor.main.df_irena_c['iso_code'] == iso].copy()
                    if not df_irena_cap_iso.empty:
                        cap_pivot_irena = df_irena_cap_iso.pivot_table(
                            index=['model_fuel'], columns='Year', values='Electricity statistics (MW/GWh)', aggfunc='sum'
                        ).reset_index()
                        
                        # Convert MW to GW
                        numeric_cols = cap_pivot_irena.select_dtypes(include=[np.number]).columns
                        cap_pivot_irena[numeric_cols] = cap_pivot_irena[numeric_cols] / 1000
                        
                        ws.range(f'A{current_row-1}').value = "IRENA Capacity (GW)"
                        ws.range(f'A{current_row}').value = [cap_pivot_irena.columns.tolist()] + cap_pivot_irena.values.tolist()
                        
                        data_shape = (len(cap_pivot_irena) + 1, len(cap_pivot_irena.columns))
                        self.format_energy_sector_table(ws, f'A{current_row}', data_shape, 
                                                       has_veda_marker=True, marker_offset=(-1, 0), dataframe=cap_pivot_irena, add_branding=False)
                        
                        current_row += len(cap_pivot_irena) + 3
                # rename electricity statistics (MW/GWh) to value column
                df_irena_cap_iso = df_irena_cap_iso.rename(columns={'Electricity statistics (MW/GWh)': 'Value'})
                df_irena_gen_iso = df_irena_gen_iso.rename(columns={'Electricity statistics (MW/GWh)': 'Value'})

                # divide Value by 1000
                df_irena_cap_iso['Value'] = df_irena_cap_iso['Value'] / 1000
                df_irena_gen_iso['Value'] = df_irena_gen_iso['Value'] / 1000
                

                df_irena_cap_iso['Unit'] = 'GW'
                df_irena_gen_iso['Unit'] = 'TWh'

                # add IRENA data to df_historical_long (for solar/windon/windoff)
                df_historical_long = pd.concat([df_historical_long, df_irena_cap_iso[df_irena_cap_iso['model_fuel'] == 'solar']])
                df_historical_long = pd.concat([df_historical_long, df_irena_gen_iso[df_irena_gen_iso['model_fuel'] == 'solar']])
                df_historical_long = pd.concat([df_historical_long, df_irena_cap_iso[df_irena_cap_iso['model_fuel'] == 'windon']])
                df_historical_long = pd.concat([df_historical_long, df_irena_gen_iso[df_irena_gen_iso['model_fuel'] == 'windon']])
                df_historical_long = pd.concat([df_historical_long, df_irena_cap_iso[df_irena_cap_iso['model_fuel'] == 'windoff']])
                df_historical_long = pd.concat([df_historical_long, df_irena_gen_iso[df_irena_gen_iso['model_fuel'] == 'windoff']])


                # --- EMBER Utilization Factors ---
                df_ember_util_iso = df_ember_util[df_ember_util['iso_code'] == iso]
                if not df_ember_util_iso.empty:
                    util_pivot = df_ember_util_iso.pivot_table(
                        index=['model_fuel'], columns='year', values='utilization_factor'
                    ).reset_index()
                    
                    # Write title and data
                    ws.range(f'A{current_row-1}').value = "EMBER Utilization Factors"
                    ws.range(f'A{current_row}').value = [util_pivot.columns.tolist()] + util_pivot.values.tolist()
                    
                    # Apply professional formatting
                    data_shape = (len(util_pivot) + 1, len(util_pivot.columns))
                    self.format_energy_sector_table(ws, f'A{current_row}', data_shape, 
                                                   has_veda_marker=True, marker_offset=(-1, 0), dataframe=util_pivot)
                    
                    # Format as percentages for utilization factors
                    if len(util_pivot.columns) > 1:
                        data_range = ws.range(f'B{current_row + 1}').resize(len(util_pivot), len(util_pivot.columns) - 1)
                        data_range.number_format = '0.0%'
                    
                    current_row += len(util_pivot) + 3
                
                # --- IRENA Utilization Factors ---
                df_irena_util_iso = df_irena_util[df_irena_util['iso_code'] == iso]
                if not df_irena_util_iso.empty:
                    util_pivot = df_irena_util_iso.pivot_table(
                        index=['model_fuel'], columns='year', values='utilization_factor'
                    ).reset_index()
                    
                    ws.range(f'A{current_row-1}').value = "IRENA Utilization Factors"
                    ws.range(f'A{current_row}').value = [util_pivot.columns.tolist()] + util_pivot.values.tolist()
                    
                    data_shape = (len(util_pivot) + 1, len(util_pivot.columns))
                    self.format_energy_sector_table(ws, f'A{current_row}', data_shape, 
                                                   has_veda_marker=True, marker_offset=(-1, 0), dataframe=util_pivot, add_branding=False)
                    
                    if len(util_pivot.columns) > 1:
                        data_range = ws.range(f'B{current_row + 1}').resize(len(util_pivot), len(util_pivot.columns) - 1)
                        data_range.number_format = '0.0%'
                    
                    current_row += len(util_pivot) + 3
                
                # --- Electricity Trade Data ---
                from iso_processing_functions import get_electricity_trade_data
                df_trade, data_source = get_electricity_trade_data(iso_processor)
                if not df_trade.empty:

                    ws.range(f'A{current_row-1}').value = f"Electricity Trade Data (TWh) - Source: {data_source}"
                    ws.range(f'A{current_row}').value = [df_trade.columns.tolist()] + df_trade.values.tolist()
                    
                    data_shape = (len(df_trade) + 1, len(df_trade.columns))
                    self.format_energy_sector_table(ws, f'A{current_row}', data_shape, 
                                                   has_veda_marker=True, marker_offset=(-1, 0), dataframe=df_trade, add_branding=False)
                
                wb.app.calculate()  # Refresh formulas

                # Unpivot the trade data and append it to the historical_data_long df,
                # but ensure the columns match (model_fuel, Year, Unit, Value)
                if not df_trade.empty:
                    # Identify year columns (all columns except 'ISO' and 'attribute')
                    id_vars = ['ISO', 'attribute']
                    value_vars = [col for col in df_trade.columns if col not in id_vars]
                    df_trade_unpivoted = df_trade.melt(
                        id_vars=id_vars, value_vars=value_vars,
                        var_name='Year', value_name='Value'
                    )
                    # Rename columns to match historical long format
                    df_trade_unpivoted = df_trade_unpivoted.rename(
                        columns={'attribute': 'model_fuel'}
                    )
                    # Add Unit column if not present, set to 'TWh'
                    if 'Unit' not in df_trade_unpivoted.columns:
                        df_trade_unpivoted['Unit'] = 'TWh'
                    # Reorder columns to match expected order
                    df_trade_unpivoted = df_trade_unpivoted[['model_fuel', 'Year', 'Unit', 'Value']]
                    # Append to historical long dataframe
                    df_historical_long = pd.concat([df_historical_long, df_trade_unpivoted], ignore_index=True)

                # Create or clear historical_data sheet
                if 'historical_data_long' in [ws.name for ws in wb.sheets]:
                    ws = wb.sheets['historical_data_long']
                    ws.clear()
                else:
                    ws = wb.sheets.add('historical_data_long')
                # Only write fields: model_fuel, year, unit, value

                df_hist = df_historical_long[['model_fuel', 'Year', 'Unit', 'Value']].copy()
                ws.range('B3').value = [df_hist.columns.tolist()] + df_hist.values.tolist()

                data_shape = (len(df_hist) + 1, len(df_hist.columns))
                self.format_energy_sector_table(ws, f'B3', data_shape, 
                                               has_veda_marker=True, marker_offset=(-1, 0), dataframe=df_hist, add_branding=False)
                print(f"✅ Historical data sheet created with professional Energy Sector formatting")

                
        except Exception as e:
            print(f"Warning: Could not create historical data sheet: {e}")

    # def update_base_vs_historical_data(self, base_vs_path, base_year_data_df):
    #     """
    #     Update Base VS file with historical_data_long sheet using professional formatting.
    #     """
    #     try:
    #         with self.workbook(base_vs_path) as wb:
    #             print("📊 Writing historical_data_long to Base VS file with professional formatting...")
                
    #             # Create or clear historical_data_long sheet
    #             if "historical_data_long" in [ws.name for ws in wb.sheets]:
    #                 wb.sheets["historical_data_long"].clear()
    #                 ws_hist = wb.sheets["historical_data_long"]
    #             else:
    #                 ws_hist = wb.sheets.add("historical_data_long")
                
    #             # Apply VerveStacks branding to the historical_data_long sheet
    #             self.add_vervestacks_branding(ws_hist)
                
    #             # Write the historical data with formatting
    #             current_row = 3
                
    #             if len(base_year_data_df) > 0:
    #                 # Write the main data
    #                 ws_hist.range(f'A{current_row}').value = [base_year_data_df.columns.tolist()] + base_year_data_df.values.tolist()
                    
    #                 # Apply Energy Sector formatting to the main data
    #                 data_shape = (len(base_year_data_df) + 1, len(base_year_data_df.columns))
    #                 self.format_energy_sector_table(ws_hist, f'A{current_row}', data_shape, 
    #                                                has_veda_marker=True, dataframe=base_year_data_df, add_branding=False)
                
    #             wb.app.calculate()  # Refresh formulas
    #             print("✅ historical_data updated in Base VS file with professional formatting")
                
    #     except Exception as e:
    #         print(f"Warning: Could not update Base VS historical data: {e}")

    def copy_historical_data(self, source_iso_path, dest_file_path, input_iso):
        """
        Copy historical_data_long sheet from source ISO file to destination file with all formatting preserved.
        Also creates ATS_Final table in ReportDefs_vervestacks.xlsx with historical data.
        
        Args:
            source_iso_path: Path to the VerveStacks_ISO.xlsx file (source)
            dest_file_path: Path to the destination file (NGFS, Base VS, etc.)
            input_iso: ISO country code (e.g., 'CHE', 'DEU')
        """
        try:
            print(f"📋 Copying historical_data_long from {source_iso_path} to {dest_file_path}...")
            
            # Open both files
            app = xw.App(visible=False)
            try:
                source_wb = app.books.open(source_iso_path)
                dest_wb = app.books.open(dest_file_path)
                
                # Check if source has historical_data sheet
                if 'historical_data_long' not in [ws.name for ws in source_wb.sheets]:
                    print("⚠️  No historical_data_long sheet found in source file")
                    return False
                
                source_sheet = source_wb.sheets['historical_data_long']
                
                # Clear or create destination sheet
                if 'historical_data_long' in [ws.name for ws in dest_wb.sheets]:
                    dest_sheet = dest_wb.sheets['historical_data_long']
                    dest_sheet.clear()
                else:
                    dest_sheet = dest_wb.sheets.add('historical_data_long')
                
                # Find the used range in source sheet
                used_range = source_sheet.used_range
                if used_range is not None:
                    # Copy the entire used range with formatting
                    used_range.copy()
                    dest_sheet.range('A1').paste()
                    
                    print(f"✅ Copied {used_range.address} from historical_data_long sheet with all formatting")
                else:
                    print("⚠️  No data found in source historical_data_long sheet")
                
                # Extract dataframe from historical_data_long sheet before closing
                # Data starts at B3 with headers
                df_historical_long = None
                try:
                    # Read the range starting from B3 (skip branding row and buffer)
                    data_range = source_sheet.range('B3').expand('table')
                    data_values = data_range.value
                    
                    if data_values:
                        # Convert to DataFrame (first row is headers)
                        if isinstance(data_values[0], list):
                            # Multiple rows
                            headers = data_values[0]
                            data_rows = data_values[1:]
                            df_historical_long = pd.DataFrame(data_rows, columns=headers)
                        else:
                            # Single row (unlikely but handle it)
                            df_historical_long = pd.DataFrame([data_values[1:]], columns=[data_values[0]])
                        
                        print(f"✅ Extracted historical_data_long dataframe: {len(df_historical_long)} rows, {len(df_historical_long.columns)} columns")
                except Exception as extract_error:
                    print(f"⚠️  Could not extract dataframe from historical_data_long: {extract_error}")
                
                # Save the destination file
                dest_wb.save()
                
                # Close files
                source_wb.close()
                dest_wb.close()

                # create ATS_Final table in the ReportDefs_vervestacks file from historical_data_long
                # Navigate from dest_file_path (e.g., SuppXLS/Scen_Base_VS.xlsx) to model root folder
                from pathlib import Path
                dest_file = Path(dest_file_path)
                model_folder = dest_file.parent.parent  # Go up from SuppXLS to model root
                reportdefs_path = model_folder / "ReportDefs_vervestacks.xlsx"

                # make the df_historical_long ready for the ATS_Final table
                df_historical_long = df_historical_long.rename(columns={'model_fuel': 'Tech_by_fuel', 'Value': 'val'})
                
                # Add scen column
                df_historical_long['scen'] = 'History'
                
                # Add varbl column based on Unit
                def get_varbl(unit):
                    if unit == 'TWh':
                        return 'Elec Production'
                    elif unit == 'GW':
                        return 'Elec Capacity'
                    else:
                        return 'CO2_emission'
                
                df_historical_long['varbl'] = df_historical_long['Unit'].apply(get_varbl)
                
                # Add model column based on Tech_by_fuel
                df_historical_long['model'] = df_historical_long['Tech_by_fuel'].apply(
                    lambda x: 'IRENA' if x in ['solar', 'windon', 'windoff'] else 'EMBER'
                )
                
                # Add region column
                df_historical_long['region'] = input_iso

                # Write ATS_Final table to ReportDefs_vervestacks.xlsx using the existing app
                if reportdefs_path.exists():
                    try:
                        reportdefs_wb = app.books.open(str(reportdefs_path))
                        
                        if 'ATS' in [ws.name for ws in reportdefs_wb.sheets]:
                            ws = reportdefs_wb.sheets['ATS']
                            ws.clear()
                        else:
                            ws = reportdefs_wb.sheets.add('ATS')
                        
                        # Write the ATS_Final table with formatting
                        # Marker will be at A1, data starts at A2
                        self.write_formatted_table(ws, "A2", df_historical_long, veda_marker="~ATS_final")
                        
                        # Save and close ReportDefs
                        reportdefs_wb.save()
                        reportdefs_wb.close()
                        
                        print(f"✅ ATS_Final table written to ReportDefs_vervestacks.xlsx: {reportdefs_path}")
                    except Exception as reportdefs_error:
                        print(f"⚠️  Could not write ATS_Final table: {reportdefs_error}")
                else:
                    print(f"⚠️  ReportDefs file not found at {reportdefs_path}, skipping ATS_Final table")
                                
                return True
                
            finally:
                app.quit()

        except Exception as e:
            print(f"Warning: Could not copy historical_data_long: {e}")
            return False

    # This function can be safely removed, as it is only a placeholder and not called elsewhere.
    def write_side_by_side_tables(self, worksheet, left_table, right_table, 
                                  left_marker=None, right_marker=None, 
                                  start_row=3, gap_columns=3):
        """
        Write two tables side-by-side with professional formatting.
        
        Args:
            worksheet: xlwings worksheet object
            left_table: pandas DataFrame for left table
            right_table: pandas DataFrame for right table  
            left_marker: VEDA marker for left table (e.g., "~fi_t")
            right_marker: VEDA marker for right table (e.g., "~fi_process")
            start_row: Row to start writing data (1-indexed)
            gap_columns: Number of empty columns between tables
        """
        try:
            # Write left table
            left_start_col = 1  # Column A
            if left_marker:
                worksheet.range(f"{self._col_letter(left_start_col)}{start_row-1}").value = left_marker
            
            # Write left table data
            data_range = f"{self._col_letter(left_start_col)}{start_row}"
            worksheet.range(data_range).value = [left_table.columns.tolist()] + left_table.values.tolist()
            
            # Format left table
            left_end_col = left_start_col + len(left_table.columns) - 1
            left_end_row = start_row + len(left_table)
            left_range = f"{self._col_letter(left_start_col)}{start_row}:{self._col_letter(left_end_col)}{left_end_row}"
            left_data_shape = (len(left_table) + 1, len(left_table.columns))  # +1 for header row
            
            # Calculate total width for branding (includes both tables)
            right_start_col = left_end_col + gap_columns + 1
            right_end_col = right_start_col + len(right_table.columns) - 1
            total_width = max(right_end_col, 12)  # At least 12 columns
            
            # Add branding once for the whole sheet
            self.add_vervestacks_branding(worksheet, start_col='A', merge_cols=total_width)
            
            self.format_energy_sector_table(worksheet, left_range, left_data_shape, add_branding=False)
            self.apply_smart_number_formatting(worksheet, left_range, left_table)
            
            # Write right table  
            right_start_col = left_end_col + gap_columns + 1
            if right_marker:
                worksheet.range(f"{self._col_letter(right_start_col)}{start_row-1}").value = right_marker
                
            # Write right table data
            data_range = f"{self._col_letter(right_start_col)}{start_row}"
            worksheet.range(data_range).value = [right_table.columns.tolist()] + right_table.values.tolist()
            
            # Format right table
            right_end_col = right_start_col + len(right_table.columns) - 1
            right_end_row = start_row + len(right_table)
            right_range = f"{self._col_letter(right_start_col)}{start_row}:{self._col_letter(right_end_col)}{right_end_row}"
            right_data_shape = (len(right_table) + 1, len(right_table.columns))  # +1 for header row
            self.format_energy_sector_table(worksheet, right_range, right_data_shape, add_branding=False)
            self.apply_smart_number_formatting(worksheet, right_range, right_table)
            
            # Apply subdued styling to VEDA markers
            if left_marker:
                marker_cell = worksheet.range(f"{self._col_letter(left_start_col)}{start_row-1}")
                marker_cell.font.name = "Consolas"
                marker_cell.font.size = 7  # Reduced by 2pt (was 9)
                marker_cell.font.italic = True
                marker_cell.font.color = (150, 150, 150)
                
            if right_marker:
                marker_cell = worksheet.range(f"{self._col_letter(right_start_col)}{start_row-1}")
                marker_cell.font.name = "Consolas"
                marker_cell.font.size = 7  # Reduced by 2pt (was 9)
                marker_cell.font.italic = True
                marker_cell.font.color = (150, 150, 150)
            
        except Exception as e:
            print(f"Warning: Error writing side-by-side tables: {e}")

    def _col_letter(self, col_num):
        """Convert column number to Excel column letter (1=A, 2=B, etc.)."""
        if col_num <= 26:
            return chr(64 + col_num)
        else:
            # Handle columns beyond Z (AA, AB, etc.)
            first = chr(64 + ((col_num - 1) // 26))
            second = chr(65 + ((col_num - 1) % 26))
            return first + second

    def write_vt_workbook(self, vt_path, tables_dict):
        """
        Create a complete VT workbook with professional formatting using evolved AUTO_ROW10 approach.
        
        Tables are automatically positioned on row 10 with proper spacing, coordinated branding,
        and smart number formatting.
        
        Args:
            vt_path: Path for the VT Excel file
            tables_dict: Dictionary with sheet data:
                {
                    'existing_stock': (fi_t, fi_p),
                    'ccs_retrofits': (fi_t_ccs, fi_p_ccs),
                    'weo_pg': (fi_t_weo, fi_p_weo)
                }
        """
        try:
            with self.workbook(vt_path, create_new=True) as wb:
                # Remove default sheet if it exists
                # if len(wb.sheets) > 0 and wb.sheets[0].name.startswith('Sheet'):
                #     wb.sheets[0].delete()
                    
                # Create and populate each sheet
                for sheet_name, (left_table, right_table) in tables_dict.items():
                    ws = wb.sheets.add(sheet_name)
                    
                    # Write tables using evolved AUTO_ROW10 approach
                    self.write_formatted_table(ws, "AUTO_ROW10", left_table, "~fi_t")
                    self.write_formatted_table(ws, "AUTO_ROW10", right_table, "~fi_process")
                    
                    # Add column comments for existing_stock sheet
                    if sheet_name == 'existing_stock':
                        self.add_column_comments(ws, 'vervestacks_ISO', 'existing_stock', data_start_row=11)
                    
                # Calculate formulas
                wb.app.calculate()
                print(f"✅ VT workbook created with professional formatting: {vt_path}")
                
        except Exception as e:
            print(f"❌ Error creating VT workbook: {e}")
            raise

    def create_electricity_trade_capacity(self, input_iso, iso_processor=None):
        """
        Create electricity import/export processes table with years pivoted
        
        Args:
            input_iso: ISO code for the country
            iso_processor: Optional ISOProcessor instance for grid_modeling configuration
        
        Returns: DataFrame with process names and total capacities by year (in GW)
        - Trd_electricity_imp: Sum of all import capacities  
        - Trd_electricity_exp: Sum of all export capacities
        """
        from shared_data_loader import get_shared_loader
        import pandas as pd
        
        # Load NTC data
        df_ntc = pd.read_csv("data/ember/europe_interconnection_data/Interconnectors/REF_NTC.csv")
        
        # Get ISO2 code (NTC data uses ISO2)
        if len(input_iso) == 3:
            # Convert ISO3 to ISO2 using region mapping
            region_map = get_shared_loader("data/").get_vs_mappings_sheet('kinesys_region_map')
            iso3_to_iso2 = dict(zip(region_map['iso'], region_map['2-alpha code']))
            iso2_code = iso3_to_iso2.get(input_iso, input_iso[:2])
        else:
            iso2_code = input_iso
        
        # Filter connections for this country
        connections = df_ntc[(df_ntc['From'] == iso2_code) | (df_ntc['To'] == iso2_code)]
        
        if connections.empty:
            print(f"ℹ️  No electricity interconnections found for {iso2_code}")
            return pd.DataFrame()  # Return completely empty DataFrame
        
        # Calculate totals by year
        results = []
        for year in sorted(connections['Year'].unique()):
            year_data = connections[connections['Year'] == year]
            
            # Total import capacity (where this country receives) - convert MW to GW
            import_total = year_data[year_data['To'] == iso2_code]['NTC_F'].sum() / 1000
            
            # Total export capacity (where this country sends) - convert MW to GW  
            export_total = year_data[year_data['From'] == iso2_code]['NTC_F'].sum() / 1000
            
            results.extend([
                    {'process': 'Trd_electricity import', 'year': year, 'capacity': import_total, 'limtype': 'lo'},
                    {'process': 'Trd_electricity export', 'year': year, 'capacity': export_total, 'limtype': 'lo'}
                ])
        
        # Pivot years as columns
        df = pd.DataFrame(results)
        pivot_df = df.pivot(index=['process', 'limtype'], columns='year', values='capacity').reset_index().fillna(0)
        
        pivot_df['attribute'] = 'cap_bnd'

        return pivot_df

    def update_scenario_files(self, dest_folder, input_iso, ngfs_data_df, base_year_data_df=None, iso_processor=None):
        """
        Update NGFS scenario files with NGFS data and historical data.
        
        Args:
            dest_folder: Path to destination folder
            input_iso: ISO code
            ngfs_data_df: NGFS data DataFrame
            base_year_data_df: Optional base year data DataFrame
            iso_processor: Optional ISOProcessor instance for grid_modeling configuration
        """
        try:
            ngfs_output_path = dest_folder / "SuppXLS/Scen_Par-NGFS.xlsx"
            
            print(f"📊 Opening NGFS file with xlwings: {ngfs_output_path}")
            # Match original notebook behavior - assume file exists from template copy
                
            with self.workbook(ngfs_output_path) as wb:
                
                print("📝 Adding ngfs_scenarios sheet...")
                # Add/update ngfs_scenarios sheet
                if "ngfs_scenarios" in [ws.name for ws in wb.sheets]:
                    wb.sheets["ngfs_scenarios"].clear()
                    ws_ngfs = wb.sheets["ngfs_scenarios"]
                else:
                    ws_ngfs = wb.sheets.add("ngfs_scenarios")
                
                # Write NGFS data with simple formatting (avoid complex operations that might hang)
                print("📊 Writing NGFS data...")
                ws_ngfs.range("A1").value = [ngfs_data_df.columns.tolist()] + ngfs_data_df.values.tolist()

                # write median values for NGFS scenarios on sheet ngfs_median
                if "ngfs_median" in [ws.name for ws in wb.sheets]:
                    wb.sheets["ngfs_median"].clear()
                    ws_ngfs_median = wb.sheets["ngfs_median"]
                else:
                    ws_ngfs_median = wb.sheets.add("ngfs_median")
                
                # Calculate median values across models for each scenario
                from data_utils import calculate_median_across_columns
                
                # Replace nulls in 'commodity' column with 'NA'
                ngfs_data_df['commodity'] = ngfs_data_df['commodity'].fillna('na')
                                
                # Calculate median across models (function auto-excludes columns with nulls)
                median_df = calculate_median_across_columns(
                    ngfs_data_df, 
                    value_cols=['value'],
                    median_across=['Model']
                )
                
                # Write median data to sheet
                print("📊 Writing NGFS median data...")
                if not median_df.empty:
                    ws_ngfs_median.range("A1").value = [median_df.columns.tolist()] + median_df.values.tolist()
                    print(f"📊 Successfully wrote {len(median_df)} rows to ngfs_median sheet")
                else:
                    print("⚠️ Median dataframe is empty - nothing to write")
                
                
                # Copy historical_data sheet from source ISO file 
                if base_year_data_df is not None:
                    wb.save()  # Save current progress
                    
            # Close the current context and copy historical data
            # if base_year_data_df is not None:
            #     # Copy from source ISO file - use absolute path resolution
            #     from pathlib import Path
            #     source_iso_path = Path("output") / f"VerveStacks_{input_iso}.xlsx"
            #     source_iso_path = source_iso_path.resolve()  # Convert to absolute path
                
            #     if source_iso_path.exists():
            #         self.copy_historical_data(str(source_iso_path), str(ngfs_output_path), input_iso)
            #     else:
            #         print(f"⚠️  Source ISO file not found: {source_iso_path}")
            
            # Final operations in a fresh context
            with self.workbook(ngfs_output_path) as wb:
                
                # Add electricity trade data to Veda sheet
                print("⚡ Adding electricity trade data to Veda sheet...")
                try:
                    trade_df = self.create_electricity_trade_capacity(input_iso, iso_processor)
                    
                    if not trade_df.empty:
                        # Get or create Veda sheet
                        if "Veda" in [ws.name for ws in wb.sheets]:
                            ws_veda = wb.sheets["Veda"]
                        else:
                            ws_veda = wb.sheets.add("Veda")
                        
                        # Find the last used row in the sheet
                        try:
                            # Get the used range to find last row with data
                            used_range = ws_veda.used_range
                            if used_range is not None:
                                last_used_row = used_range.last_cell.row
                            else:
                                last_used_row = 0
                        except:
                            # Fallback: manually check for last used row
                            last_used_row = 0
                            for row in range(1, 101):  # Check first 100 rows
                                try:
                                    if (ws_veda.range(f'A{row}').value is not None or 
                                        ws_veda.range(f'B{row}').value is not None or
                                        ws_veda.range(f'C{row}').value is not None):
                                        last_used_row = row
                                except:
                                    break
                        
                        # Write one row after the last used row
                        current_row = last_used_row + 5
                        
                        # Use ExcelManager's write_formatted_table method
                        try:
                            self.write_formatted_table(
                                ws_veda, 
                                f'Q{current_row}', 
                                trade_df, 
                                veda_marker="~tfm_ins-ts"
                            )
                            print(f"✅ Electricity trade data written to Veda sheet at row {current_row}")
                            
                        except Exception as write_error:
                            print(f"⚠️  Error writing trade data to Veda sheet: {write_error}")
                            # Fallback to simple write if formatted table fails
                    else:
                        print("ℹ️  No electricity trade data to write")
                        
                except Exception as trade_error:
                    print(f"⚠️  Error creating electricity trade data: {trade_error}")
                
                print("🔄 Calculating formulas...")
                wb.app.calculate()
                print(f"✅ NGFS scenario file updated: {ngfs_output_path}")
                return True
                
        except Exception as e:
            print(f"❌ Error updating scenario files: {e}")
            return False

    def write_buildrate_assumptions(self, base_vs_path, buildrate_assumptions_df):
        """
        Write buildrate assumptions to the buildrates sheet in Base VS file.
        
        Args:
            base_vs_path: Path to the Base VS Excel file
            buildrate_assumptions_df: DataFrame with buildrate data filtered for the ISO
        """
        try:
            # Check if we have data to write
            if buildrate_assumptions_df.empty:
                print("ℹ️  No buildrate assumptions found for this ISO")
                return
            
            with self.workbook(base_vs_path) as wb:
                # Create or get buildrates sheet
                sheet_names = [s.name for s in wb.sheets]
                
                if "buildrates" in sheet_names:
                    ws = wb.sheets["buildrates"]
                    # Clear existing content but preserve any formatting in other areas
                    try:
                        ws.range("B10:Z12").clear()
                    except:
                        pass
                else:
                    ws = wb.sheets.add("buildrates")
                
                # Write the buildrate assumptions data starting at B10 with professional formatting
                self.write_formatted_table(ws, "B10", buildrate_assumptions_df, "BUILD RATE ASSUMPTIONS")
                
                # Add sheet documentation if this is a new sheet
                if "buildrates" not in sheet_names:
                    self.add_sheet_documentation(ws, 'vervestacks_ISO', 'buildrates', add_documentation=True)
                
                print(f"✅ Buildrate assumptions written to buildrates sheet at B10: {len(buildrate_assumptions_df)} records")
                
        except Exception as e:
            print(f"⚠️  Warning: Could not write buildrate assumptions: {e}")

    def write_grid_geolocation_data(self, reportdefs_path, df_geolocation, df_region_com_geolocation):
        """
        Write geolocation data to SysSettings file for grid modeling.
        
        Args:
            reportdefs_path: Path to the ReportDefs_vervestacks.xlsx file
            df_geolocation: DataFrame with region, lat, lng columns
        """
        try:
            # Check if we have data to write
            if df_geolocation.empty:
                print("ℹ️  No geolocation data found")
                return
            
            with self.workbook(reportdefs_path) as wb:
                # Create or get geolocation sheet
                sheet_names = [s.name for s in wb.sheets]
                
                if "geolocation" in sheet_names:
                    ws = wb.sheets["geolocation"]
                    # Clear existing content
                    try:
                        ws.range("B10:E100").clear()
                    except:
                        pass
                else:
                    ws = wb.sheets.add("geolocation")
                
                # Write the geolocation data starting at B3 with professional formatting
                self.write_formatted_table(ws, "AUTO_ROW10", df_geolocation, "~geolocation")
                self.write_formatted_table(ws, "AUTO_ROW10", df_region_com_geolocation, "~geolocation")
                
                print(f"✅ Geolocation data written to ReportDefs geolocation sheet: {len(df_geolocation)} records")
                
        except Exception as e:
            print(f"⚠️  Warning: Could not write geolocation data: {e}")

    def write_grid_geo_sets(self, sets_vervestacks_path, df_set_psetco):
        """
        Write geographic set definitions to Sets-vervestacks file for grid modeling.
        
        Args:
            sets_vervestacks_path: Path to the Sets-vervestacks.xlsx file
            df_set_psetco: DataFrame with setname, pset_co columns
        """
        try:
            # Check if we have data to write
            if df_set_psetco.empty:
                print("ℹ️  No geographic set data found")
                return
            
            with self.workbook(sets_vervestacks_path) as wb:
                # Create or get geo_sets sheet
                sheet_names = [s.name for s in wb.sheets]
                
                if "geo_sets" in sheet_names:
                    ws = wb.sheets["geo_sets"]
                    # Clear existing content
                    try:
                        ws.range("B10:Z100").clear()
                    except:
                        pass
                else:
                    ws = wb.sheets.add("geo_sets")
                
                # Write the geographic set data starting at B3 with professional formatting
                self.write_formatted_table(ws, "AUTO_ROW10", df_set_psetco, "~tfm_psets")
                
                print(f"✅ Geographic sets written to Sets-vervestacks geo_sets sheet: {len(df_set_psetco)} records")
                
        except Exception as e:
            print(f"⚠️  Warning: Could not write geographic sets: {e}")

    def write_grid_process_map_geo(self, reportdefs_path, df_set_psetco, df_admin_mapping, df_region_com_dimension):
        """
        Write process mapping for geographic visualization to ReportDefs file for grid modeling.
        
        Args:
            reportdefs_path: Path to the ReportDefs_vervestacks.xlsx file
            df_set_psetco: DataFrame with setname, pset_co columns
        """
        try:
            # Check if we have data to write
            if df_set_psetco.empty:
                print("ℹ️  No geographic set data found for process mapping")
                return
            
            # Create process mapping DataFrame
            df_process_map = pd.DataFrame({
                'dimension': 'grid_node',
                'description': df_set_psetco['setname'],
                'pset_set': df_set_psetco['setname']
            })
            
            with self.workbook(reportdefs_path) as wb:
                # Create or get process_map_geo sheet
                sheet_names = [s.name for s in wb.sheets]
                
                if "process_map_geo" in sheet_names:
                    ws = wb.sheets["process_map_geo"]
                    # Clear existing content
                    try:
                        ws.range("B10:Z100").clear()
                    except:
                        pass
                else:
                    ws = wb.sheets.add("process_map_geo")
                
                # Write the process mapping data starting at B3 with professional formatting
                self.write_formatted_table(ws, "AUTO_ROW10", df_process_map, "~process_map")
                self.write_formatted_table(ws, "AUTO_ROW10", df_admin_mapping, "~process_map")
                self.write_formatted_table(ws, "AUTO_ROW10", df_region_com_dimension, "~commodity_map")
                
                print(f"✅ Process mapping written to ReportDefs process_map_geo sheet: {len(df_process_map)} records")
                
        except Exception as e:
            print(f"⚠️  Warning: Could not write process mapping: {e}")


# Convenience instance for easy importing
excel_manager = ExcelManager()