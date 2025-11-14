# VerveStacks Batch Processing Guide

This guide covers the batch processing scripts for creating multiple ISO country models efficiently.

## 🎯 Quick Start

### Simple Usage (Recommended for most users)

```bash
# Process sample countries (JPN, DEU, USA, CHN, IND)
python quick_batch.py sample

# Process EU countries
python quick_batch.py eu

# Process specific countries
python quick_batch.py custom JPN,DEU,USA
```

### Advanced Usage

```bash
# Process G20 countries with parallel processing
python batch_process_models.py --group G20 --parallel

# Process specific countries with custom settings
python batch_process_models.py --isos JPN,DEU,USA --capacity-threshold 50 --no-git

# Process all available countries (use with caution!)
python batch_process_models.py --process-all
```

## 📁 Files Overview

| File | Purpose | Usage Level |
|------|---------|-------------|
| `quick_batch.py` | Simple scenarios | Beginner |
| `batch_process_models.py` | Full-featured batch processing | Advanced |
| `batch_config_template.json` | Configuration template | Advanced |
| `main.py` | Single ISO processing | All levels |

## 🌍 Available Country Groups

| Group | Countries | Count |
|-------|-----------|--------|
| **SAMPLE** | JPN, DEU, USA, CHN, IND | 5 |
| **G7** | USA, JPN, DEU, GBR, FRA, ITA, CAN | 7 |
| **G20** | Major economies | 19 |
| **EU** | European Union members | 27 |
| **BRICS** | BRA, RUS, IND, CHN, ZAF | 5 |
| **ASEAN** | Southeast Asian nations | 10 |

View full list: `python batch_process_models.py --list-groups`

## ⚡ Processing Options

### Sequential vs Parallel Processing

**Sequential (Default - Recommended)**
- ✅ Stable and reliable
- ✅ Better error handling
- ✅ Easier to debug
- ❌ Slower for large batches

**Parallel (Advanced)**
- ✅ Faster processing
- ❌ May cause Excel/xlwings issues
- ❌ Uses more system resources
- ❌ Harder to debug errors

### Git Integration

By default, each country model is:
1. **Main Processing**: Creates VerveStacks_{ISO}.xlsx with energy data
2. **RE Shapes Analysis v5**: Generates renewable energy shape analysis files  
3. **Git Integration**: Created in clean branch, committed, and pushed

Disable git with `--no-git` flag, or skip RE analysis with `--skip-re-shapes` flag.

### Two-Step Processing Pipeline

Each ISO country goes through a two-step process:

**Step 1: Main Processing**
- Loads and processes energy data (IRENA, EMBER, GEM, etc.)
- Creates existing stock analysis
- Generates `VerveStacks_{ISO}.xlsx` with complete energy model data
- Sets up VEDA model files and structure

**Step 2: RE Shapes Analysis v5** 
- Uses `VerveStacks_{ISO}.xlsx` as input
- Analyzes renewable energy shapes and demand patterns
- Generates `RE_Analysis_Complete.xlsx` with:
  - Optimal modeling periods for time-slice analysis
  - Extreme abundance/scarcity periods
  - Seasonal and hourly renewable energy patterns
  - Three scenario approaches (short/medium/long spans)

The RE Shapes Analysis is crucial for time-slice modeling and renewable energy integration studies.

## 📊 Processing Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `capacity_threshold` | 100 | MW threshold for individual plant tracking |
| `efficiency_gas` | 1.0 | Gas plant efficiency adjustment factor |
| `efficiency_coal` | 1.0 | Coal plant efficiency adjustment factor |
| `tsopt` | triple_1 | Time slice configuration |

## 📝 Logging and Monitoring

Batch processing creates detailed logs in the `batch_logs/` directory:

```
batch_logs/
├── batch_process_20250131_143022.log    # Main processing log
├── batch_errors_20250131_143022.log     # Error details
└── batch_success_20250131_143022.log    # Successful completions
```

Real-time progress is shown in the console with:
- 🚀 Start notifications
- 📍 Progress indicators  
- ✅ Success confirmations
- ❌ Error alerts
- 📊 Summary statistics

## 🔧 Examples

### Basic Examples

```bash
# Test with sample countries
python quick_batch.py sample

# Process EU with no git operations
python quick_batch.py eu --no-git

# Process specific countries
python quick_batch.py custom JPN,DEU,FRA,ITA
```

### Advanced Examples

```bash
# EU countries with custom capacity threshold
python batch_process_models.py --group EU --capacity-threshold 50

# Parallel processing of G7 countries
python batch_process_models.py --group G7 --parallel --max-workers 2

# Force reload cache and overwrite existing files
python batch_process_models.py --isos CHN,IND --force-reload --overwrite

# Custom efficiency adjustments
python batch_process_models.py --isos USA,CAN --efficiency-gas 1.1 --efficiency-coal 0.9

# Skip RE Shapes Analysis for faster processing
python batch_process_models.py --group SAMPLE --skip-re-shapes
```

### Production Examples

```bash
# Process all EU countries sequentially (recommended for production)
python batch_process_models.py --group EU --output-dir production_models

# Large batch with careful logging
python batch_process_models.py --group G20 --log-dir detailed_logs --no-git
```

## ⚠️ Important Considerations

### System Requirements
- **Memory**: 8GB+ RAM recommended for large batches
- **Storage**: ~500MB per country model
- **Excel**: Microsoft Excel required (xlwings dependency)
- **Time**: 2-5 minutes per country (varies by size)

### Before Large Batches
1. Test with `--group SAMPLE` first
2. Ensure sufficient disk space
3. Close other Excel applications
4. Consider using `--no-git` for testing
5. Run during off-peak hours

### Error Recovery
- Failed countries can be reprocessed individually
- Check error logs for specific failure reasons
- Use `--overwrite` to replace failed attempts
- Consider `--force-reload` if data issues suspected

## 🚨 Troubleshooting

### Common Issues

**Excel/xlwings errors**
```bash
# Solution: Close Excel, restart, try sequential processing
python batch_process_models.py --isos FAILED_ISO --no-parallel
```

**Out of memory**
```bash
# Solution: Process smaller batches or increase system memory
python batch_process_models.py --isos SUBSET_1,SUBSET_2
```

**Git errors**
```bash
# Solution: Skip git operations during processing
python batch_process_models.py --group EU --no-git
```

**Network timeouts**
```bash
# Solution: Force reload cache or check internet connection
python batch_process_models.py --isos ISO --force-reload
```

### Getting Help

```bash
# Show all available options
python batch_process_models.py --help

# List available countries
python batch_process_models.py --list-available

# List country groups
python batch_process_models.py --list-groups
```

## 📈 Performance Tips

1. **Use SSD storage** for better I/O performance
2. **Close unnecessary applications** to free memory
3. **Process during off-peak hours** for better system performance
4. **Start with small batches** to verify configuration
5. **Monitor system resources** during large batches
6. **Use sequential processing** for stability
7. **Consider batch size** (5-10 countries per batch for large datasets)

## 🔄 Resuming Failed Batches

If a batch fails partway through:

```bash
# Check which countries completed successfully
cat batch_logs/batch_success_*.log

# Process only the failed countries
python batch_process_models.py --isos FAILED1,FAILED2,FAILED3
```

The system automatically skips existing outputs unless `--overwrite` is specified.

---

For questions or issues, check the main VerveStacks documentation or examine the detailed log files in `batch_logs/`.
