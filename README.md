# Subtitle Gap Remover

A Python script that processes SRT subtitle files to remove gaps between subtitle entries, ensuring seamless viewing experience. I find it very annoying when subtitle text has gaps in between snippets. Sometimes, text disappears unnecessarily quickly and I can't read all of it. During the gaps, there is no text anymore, but I could be reading the text at a more comfortable pace if it stayed on the screen with no gaps to begin with. This script quickly removes the gaps and solves that issue.

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

## Executing script from any directory

Here's how I recommend you execute the script from any directory:

#### **On Windows:**

1. Set an environment variable to the directory of the script:

   a. Press `Win + R` to open the Run dialog

   b. Type `sysdm.cpl ,3` and press Enter

   c. Click on the `Environment Variables` button
   
   d. Click the `New` button under the `User variables` section.

   e. Name the variable something that makes it clear what it is, like `SUBREM` for Subtitle Gap Remover.

   f. Set the variable value to the full path of the Python script.

**Note:** You don't need to create an environment variable, but it prevents needing to explicitly define the full path in the next step (where I specify `%SUBREM%`).

2. I recommend setting the command line alias in Powershell since it's easy to permanently store.

   a. Open a Powershell shell.

   b. Open the profile file for editing. You can do this by running `notepad $PROFILE` in the shell. The path to the file being edited is `$PROFILE`. You can check the path by running `echo $PROFILE` in the shell.

   c. Add the following line to the file (assuming `subrem` is the name of the command you want to use globally):

   ```powershell
   function subrem { python "%SUBREM%\subtitle_gap_remover.py" $args[0] }
   ```

   d. Save the file and exit the text editor.

   e. Close and reopen the Powershell shell to apply the changes. It should work anywhere now.

#### **On Mac:**

1. Assuming you are using the default zsh shell, open the `.zshrc` file for editing.

   a. Run `nano ~/.zshrc` in the terminal. If you use VIM, you can use `vim ~/.zshrc` instead.

   b. Add the following line to the file (assuming `subrem` is the name of the command you want to use globally):

   ```zsh
   subrem() { python "/path/to/script/subtitle_gap_remover.py" "$@" }
   ```
   
   c. Save the file and exit the text editor.

   d. Close and reopen the terminal to apply the changes. It should work anywhere now. You can restart zsh by running `exec zsh` in the ZSH shell.

#### **On Linux:**

1. Assuming you are using the default bash shell, open the `.bashrc` file for editing.

   a. Run `nano ~/.bashrc` in the terminal. If you use VIM, you can use `vim ~/.bashrc` instead.

   b. Add the following line to the file (assuming `subrem` is the name of the command you want to use globally):

   ```bash
   subrem() { python "/path/to/script/subtitle_gap_remover.py" "$@" }
   ```
   
   c. Save the file and exit the text editor.

   d. Close and reopen the terminal to apply the changes. It should work anywhere now. You can restart bash by running `exec bash` in the bash shell.

## Troubleshooting

If you encounter issues:
1. Ensure you have the correct path to your SRT files
2. Verify that the SRT files are properly formatted
3. Check that you have write permissions for the files you are trying to modify
4. If the script doesn't recognize your SRT format, please check for any non-standard formatting in the files 