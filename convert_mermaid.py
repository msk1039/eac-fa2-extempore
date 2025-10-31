import sys
import re
import subprocess
import os
import argparse
import tempfile
from pathlib import Path

class DiagramConverter:
    """
    A class to handle the conversion of Mermaid code blocks found by re.sub.
    It keeps track of the diagram count and manages file paths.
    """
    def __init__(self, output_file_path: Path):
        self.counter = 0
        # The output path for the new .md file
        self.output_md_path = output_file_path
        # Get the directory where the .md file will be saved
        self.output_dir = output_file_path.parent
        # Create a subdirectory for the images
        self.image_dir = self.output_dir / "diagram_images"
        self.image_dir.mkdir(exist_ok=True)
        print(f"Saving generated images to: {self.image_dir.resolve()}")

    def __call__(self, match: re.Match) -> str:
        """
        This method is called for every match found by re.sub.
        """
        # Get the code inside the ```mermaid ... ``` block
        mermaid_code = match.group(1).strip()
        
        # If the block is empty, just return it as is
        if not mermaid_code:
            return match.group(0)

        self.counter += 1
        image_name = f"diagram_{self.counter}.png"
        
        # The final, absolute path where the image file will be saved
        image_save_path = self.image_dir / image_name
        
        # The relative path to use in the Markdown file
        # e.g., "diagram_images/diagram_1.png"
        relative_image_path = f"{self.image_dir.name}/{image_name}".replace("\\", "/")
        
        print(f"  [+] Found diagram {self.counter}. Generating {image_name}...")

        try:
            # Create a temporary file to hold the Mermaid code
            # mmdc works more reliably with file inputs
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".mmd") as temp_in:
                temp_in.write(mermaid_code)
                temp_in_path = temp_in.name
            
            # Build the mmdc command
            # mmdc -i input.mmd -o output.png
            cmd = ["mmdc", "-i", temp_in_path, "-o", str(image_save_path)]
            
            # Execute the command
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')

            if result.stderr:
                print(f"    [!] mmdc warning for diagram {self.counter}: {result.stderr.strip()}")

            # Clean up the temporary input file
            os.remove(temp_in_path)

            # Create the replacement Markdown image link
            alt_text = f"Generated Mermaid Diagram {self.counter}"
            replacement_md = f"![{alt_text}]({relative_image_path})"
            
            print(f"    [✔] Success. Replacing code block with image link.")
            return replacement_md

        except FileNotFoundError:
            print("\n" + "="*50, file=sys.stderr)
            print("Error: 'mmdc' command not found.", file=sys.stderr)
            print("Please install the Mermaid CLI tool:", file=sys.stderr)
            print("  npm install -g @mermaid-js/mermaid-cli", file=sys.stderr)
            print("="*50 + "\n", file=sys.stderr)
            sys.exit(1) # Stop the script
            
        except subprocess.CalledProcessError as e:
            print(f"    [✘] Error generating diagram {self.counter}:", file=sys.stderr)
            print(f"      Stderr: {e.stderr.strip()}", file=sys.stderr)
            print("    Keeping original code block in document.", file=sys.stderr)
            # On failure, return the original code block
            return match.group(0)
        
        except Exception as e:
            print(f"    [✘] An unexpected error occurred for diagram {self.counter}: {e}", file=sys.stderr)
            print("    Keeping original code block in document.", file=sys.stderr)
            return match.group(0)

def process_markdown_file(input_file: Path, output_file: Path):
    """
    Reads the input file, processes it, and writes to the output file.
    """
    print(f"Reading from: {input_file}")
    try:
        content = input_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    # Regex to find all Mermaid code blocks.
    # re.DOTALL makes the '.' special character match any character, including newlines.
    pattern = re.compile(r'```mermaid\s*?(.*?)```', re.DOTALL)
    
    # Create the converter instance. It will be called for each match.
    converter = DiagramConverter(output_file)
    
    # Use re.sub with our converter class to replace all matches
    modified_content = pattern.sub(converter, content)
    
    try:
        output_file.write_text(modified_content, encoding="utf-8")
        print(f"\nDone! New file created at: {output_file.resolve()}")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Finds Mermaid diagrams in a Markdown file, generates images, and replaces the code blocks with image links.",
        epilog="Example: python convert_mermaid.py my_document.md"
    )
    parser.add_argument("input_file", type=str, help="The input Markdown file (e.g., 'my_doc.md')")
    parser.add_argument(
        "-o", "--output_file", type=str, 
        help="The output Markdown file (default: '[input_name]_with_images.md')"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    
    if args.output_file:
        output_path = Path(args.output_file)
    else:
        # Create a default output name, e.g., "my_doc.md" -> "my_doc_with_images.md"
        output_path = input_path.with_name(f"{input_path.stem}_with_images{input_path.suffix}")

    if input_path.resolve() == output_path.resolve():
        print("Error: Input and output files cannot be the same. Please specify a different output file with -o", file=sys.stderr)
        sys.exit(1)

    process_markdown_file(input_path, output_path)

if __name__ == "__main__":
    main()