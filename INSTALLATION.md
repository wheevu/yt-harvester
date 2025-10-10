# Installation Guide for yt-harvester 🎬

## ✅ Package Successfully Set Up!

Your project is now a proper, installable Python package with a command-line interface.

## Project Structure

```
yt_harvester/
├── pyproject.toml              # Package configuration & metadata
├── README.md                   # Full documentation
├── requirements.txt            # Legacy dependency file
├── yt_harvester.py            # Original script (kept for reference)
└── src/
    └── yt_harvester/
        ├── __init__.py         # Package marker
        └── __main__.py         # Main executable script
```

## Installation Status

✅ **INSTALLED** - The package is already installed in editable mode!

## How to Use

### From Anywhere on Your System

```bash
# Basic usage
yt-harvester "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# With video ID only
yt-harvester dQw4w9WgXcQ

# Custom options
yt-harvester dQw4w9WgXcQ -c 10 -f json

# Get help
yt-harvester --help
```

### The Magic 🪄

When you run `yt-harvester`, Python:
1. Looks up the command in `pyproject.toml`
2. Finds: `yt-harvester = "yt_harvester.__main__:main"`
3. Executes the `main()` function from `src/yt_harvester/__main__.py`

## Development Workflow

Since you installed with `-e` (editable mode):

1. **Edit the code**: Modify `src/yt_harvester/__main__.py`
2. **Test immediately**: Run `yt-harvester` - changes take effect instantly!
3. **No reinstall needed**: Changes are reflected automatically

## Useful Commands

```bash
# Check if installed
pip list | grep yt-harvester

# Uninstall
pip uninstall yt-harvester

# Reinstall (from project root)
pip install -e .

# Install for production (not editable)
pip install .
```

## Sharing Your Package

### Option 1: Install from Git

Others can install directly from your Git repository:

```bash
pip install git+https://github.com/yourusername/yt-harvester.git
```

### Option 2: Distribute as a Wheel

```bash
# Build distribution files
pip install build
python -m build

# This creates:
# - dist/yt_harvester-0.1.0-py3-none-any.whl
# - dist/yt_harvester-0.1.0.tar.gz

# Share these files, others can install with:
pip install yt_harvester-0.1.0-py3-none-any.whl
```

### Option 3: Publish to PyPI

```bash
# Install twine
pip install twine

# Upload to PyPI (requires account)
python -m twine upload dist/*

# Then anyone can install with:
pip install yt-harvester
```

## Next Steps

1. ✅ Test the command: `yt-harvester --help`
2. ✅ Try harvesting a video: `yt-harvester dQw4w9WgXcQ -c 5`
3. Edit `pyproject.toml` to update author info, URLs, etc.
4. Update `README.md` with your specific details
5. Consider adding a LICENSE file
6. Create a `.gitignore` file (if using Git)

## Files You Can Keep/Remove

### Keep These:
- `pyproject.toml` - Required for package definition
- `README.md` - Documentation
- `src/yt_harvester/` - The actual package
- `requirements.txt` - Useful for reference

### Optional to Remove:
- `yt_harvester.py` - Original script (now duplicated in `src/yt_harvester/__main__.py`)
- Test output files: `dQw4w9WgXcQ.txt`, `QPuIysZxXwM.json`, `test_output.txt`

### Auto-Generated (Don't Edit):
- `src/yt_harvester.egg-info/` - Created by pip during installation

## Troubleshooting

### Command not found: yt-harvester

**Solution**: Ensure your Python scripts directory is in PATH:

```bash
# Check where it's installed
which yt-harvester

# Add to PATH (add to ~/.zshrc or ~/.bashrc)
export PATH="$PATH:$(python -m site --user-base)/bin"
```

### Changes not reflecting

**Solution**: Make sure you installed in editable mode:

```bash
pip uninstall yt-harvester
pip install -e .
```

### Import errors

**Solution**: Reinstall dependencies:

```bash
pip install yt-dlp youtube-transcript-api
```

## Success! 🎉

You now have a professional, installable Python package with:
- ✅ Command-line interface (`yt-harvester`)
- ✅ Proper package structure
- ✅ Automatic dependency management
- ✅ Editable development mode
- ✅ Ready for distribution

Happy harvesting! 🎬
