# Subtitle Gap Remover

A Python script that processes SRT subtitle files to remove gaps between subtitle entries, ensuring seamless viewing experience.

## Prerequisites

1. **Python 3.6+**

## Usage

Run the script with one or more SRT files as arguments:

```bash
# Process a single file (default gap mode: "after")
python subtitle_gap_remover.py "path/to/your/subtitle.srt"

# Process a single file with specific gap mode
python subtitle_gap_remover.py "path/to/your/subtitle.srt" before

# Process multiple files
python subtitle_gap_remover.py "subtitle1.srt" "subtitle2.srt" "subtitle3.srt"

# Process all SRT files in a directory
python subtitle_gap_remover.py "subtitles/*.srt"

# Process all SRT files with specific gap mode
python subtitle_gap_remover.py "subtitles/*.srt" before
```

## Gap Modes

The script supports two gap removal modes:

1. **after** (default): Adjusts the end time of each subtitle to match the start time of the next subtitle. This ensures that one subtitle ends exactly when the next one begins.

2. **before**: Adjusts the start time of each subtitle to match the end time of the previous subtitle. This ensures that each subtitle starts exactly when the previous one ends.

## Operation

The script will:
1. Parse each SRT file provided
2. Identify all subtitle entries and their timestamps
3. Adjust the timing according to the specified gap mode
4. Overwrite the original files with the modified content

## Output

The script modifies the input files directly, overwriting the original content with the gap-removed version.

## Example

Before:
```
1
00:00:00,708 --> 00:00:04,791
<b>This is the first subtitle</b>

2
00:00:05,375 --> 00:00:07,541
<b>This is the second subtitle</b>
```

After (with gap mode "after"):
```
1
00:00:00,708 --> 00:00:05,375
<b>This is the first subtitle</b>

2
00:00:05,375 --> 00:00:07,541
<b>This is the second subtitle</b>
```

## Notes

- The script preserves the original subtitle text and formatting
- It handles different file encodings (UTF-8 and Latin-1) for maximum compatibility
- The script includes detailed debugging information during processing
- When using wildcard patterns, all matching files will be processed in a single run
- The script automatically preserves the line breaks and formatting present in the original SRT files

## Troubleshooting

If you encounter issues:
1. Ensure you have the correct path to your SRT files
2. Verify that the SRT files are properly formatted
3. Check that you have write permissions for the files you are trying to modify
4. If the script doesn't recognize your SRT format, please check for any non-standard formatting in the files 