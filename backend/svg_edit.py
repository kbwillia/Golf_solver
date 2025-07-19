import os
import re

INPUT_DIR = r'C:\Users\kbwil\Documents\Kyle\Data_Projects\Golf\static\cards'
OUTPUT_DIR = r'C:\Users\kbwil\Documents\Kyle\Data_Projects\Golf\static\edited_cards'

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fix_main_border_rect(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        svg = f.read()

    # Find all <rect ...> tags
    rects = list(re.finditer(r'<rect[^>]+>', svg))
    # Try to find the one with stroke="black" and large width/height (likely the border)
    border_rect = None
    for rect in rects:
        tag = rect.group(0)
        # Look for stroke="black" or stroke='black'
        if re.search(r'stroke=[\'\"]black[\'\"]', tag):
            # Heuristic: look for large width/height (e.g., >200)
            width = float(re.search(r'width=[\'\"]([\d.]+)', tag).group(1))
            height = float(re.search(r'height=[\'\"]([\d.]+)', tag).group(1))
            if width > 100 and height > 100:
                border_rect = rect
                break
    # If found, replace its stroke with white
    if border_rect:
        start, end = border_rect.span()
        tag = border_rect.group(0)
        tag_new = re.sub(r'stroke=[\'\"]black[\'\"]', 'stroke="white"', tag)
        svg = svg[:start] + tag_new + svg[end:]
    # Write out the result
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(svg)

def batch_edit_svgs(input_dir, output_dir):
    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.svg'):
            in_path = os.path.join(input_dir, filename)
            out_path = os.path.join(output_dir, filename)
            fix_main_border_rect(in_path, out_path)
            print(f'Edited: {filename}')

if __name__ == '__main__':
    batch_edit_svgs(INPUT_DIR, OUTPUT_DIR)