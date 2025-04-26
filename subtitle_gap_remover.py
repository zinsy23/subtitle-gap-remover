#!/usr/bin/env python3
import sys
import re
import glob
import os

def parse_time(time_str):
    """Convert SRT time format to milliseconds."""
    parts = time_str.split(',')
    time_parts = parts[0].split(':')
    milliseconds = parts[1]
    hours, minutes, seconds = map(int, time_parts)
    return hours * 3600000 + minutes * 60000 + seconds * 1000 + int(milliseconds)

def format_time(milliseconds):
    """Convert milliseconds to SRT time format."""
    hours = milliseconds // 3600000
    milliseconds %= 3600000
    minutes = milliseconds // 60000
    milliseconds %= 60000
    seconds = milliseconds // 1000
    milliseconds %= 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def process_srt_file(file_path, gap_mode="after"):
    """Process an SRT file to remove gaps between subtitles."""
    print(f"Processing {file_path} with gap mode: {gap_mode}", flush=True)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            print(f"File read successfully, content length: {len(content)} characters", flush=True)
    except UnicodeDecodeError:
        print(f"UTF-8 decoding failed, trying with latin-1", flush=True)
        # Try with a different encoding if utf-8 fails
        with open(file_path, 'r', encoding='latin-1') as file:
            content = file.read()
            print(f"File read with latin-1, content length: {len(content)} characters", flush=True)
    
    # Parse the SRT file into subtitle blocks
    subtitles = []
    
    # Split the content by empty lines to get subtitle blocks
    blocks = re.split(r'\r?\n\r?\n', content.strip())
    print(f"Split content into {len(blocks)} blocks", flush=True)
    
    for i, block in enumerate(blocks):
        if i < 3 or i > len(blocks) - 3:
            print(f"Block {i}: {block[:100]}{'...' if len(block) > 100 else ''}", flush=True)
        elif i == 3:
            print("...", flush=True)
            
        lines = block.split('\n')
        if len(lines) >= 3:  # Ensure we have index, timing, and text
            index = lines[0]
            timing = lines[1]
            text = '\n'.join(lines[2:])
            
            # Parse timing
            match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', timing)
            if match:
                start_time, end_time = match.groups()
                start_ms = parse_time(start_time)
                end_ms = parse_time(end_time)
                
                subtitle = {
                    'index': index,
                    'start': start_ms,
                    'end': end_ms,
                    'text': text
                }
                subtitles.append(subtitle)
            else:
                print(f"Warning: Failed to parse timing in block {i}: {timing}", flush=True)
        else:
            print(f"Warning: Block {i} has fewer than 3 lines: {lines}", flush=True)
    
    print(f"Found {len(subtitles)} valid subtitle blocks", flush=True)
    
    # Apply gap removal
    changes_made = 0
    if len(subtitles) > 1:
        for i in range(len(subtitles) - 1):
            current = subtitles[i]
            next_subtitle = subtitles[i + 1]
            
            if gap_mode == "after":
                # Make the end time of current subtitle match the start time of next subtitle
                if current['end'] != next_subtitle['start']:
                    current['end'] = next_subtitle['start']
                    changes_made += 1
            else:  # gap_mode == "before"
                # Make the start time of next subtitle match the end time of current subtitle
                if next_subtitle['start'] != current['end']:
                    next_subtitle['start'] = current['end']
                    changes_made += 1
    
    print(f"Made {changes_made} timing changes", flush=True)
    
    # Reconstruct the SRT content
    output_content = ''
    for i, subtitle in enumerate(subtitles):
        output_content += f"{subtitle['index']}\n"
        output_content += f"{format_time(subtitle['start'])} --> {format_time(subtitle['end'])}\n"
        output_content += f"{subtitle['text']}\n"
        
        # Add blank line between subtitles except for the last one
        if i < len(subtitles) - 1:
            output_content += "\n"
    
    # Write the modified content back to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(output_content)
    
    print(f"Successfully processed {file_path}", flush=True)

def main():
    """Main function to handle command line arguments and process files."""
    print(f"Starting subtitle gap remover script", flush=True)
    print(f"Arguments: {sys.argv}", flush=True)
    
    if len(sys.argv) < 2:
        print("Usage: python subtitle_gap_remover.py <file_path(s)> [before|after]", flush=True)
        print("  file_path(s): Path(s) to SRT file(s), wildcards accepted", flush=True)
        print("  before|after: Optional gap mode, defaults to 'after'", flush=True)
        return
    
    # Check if the last argument is a gap mode
    gap_mode = "after"  # Default
    files_to_process = []
    
    if sys.argv[-1].lower() in ["before", "after"]:
        gap_mode = sys.argv[-1].lower()
        file_args = sys.argv[1:-1]
    else:
        file_args = sys.argv[1:]
    
    print(f"Gap mode: {gap_mode}", flush=True)
    print(f"File arguments: {file_args}", flush=True)
    
    # Process all file arguments, expanding wildcards
    for arg in file_args:
        expanded_files = glob.glob(arg)
        if expanded_files:
            files_to_process.extend(expanded_files)
            print(f"Expanded '{arg}' to {len(expanded_files)} file(s)", flush=True)
        else:
            print(f"Warning: No files found matching '{arg}'", flush=True)
    
    print(f"Files to process: {files_to_process}", flush=True)
    
    if not files_to_process:
        print("No files to process.", flush=True)
        return
    
    # Process each file
    for file_path in files_to_process:
        if os.path.isfile(file_path):
            process_srt_file(file_path, gap_mode)
        else:
            print(f"Warning: '{file_path}' is not a file.", flush=True)

if __name__ == "__main__":
    main() 