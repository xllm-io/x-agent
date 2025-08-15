import os
import shutil
from typing import Optional
from datetime import datetime
import requests
from urllib.parse import urlparse
from server.server import mcp
from PIL import Image as PILImage
from pydantic import Field
from mcp.server.fastmcp import Context
from mcp.server.fastmcp.utilities.types import Image
import logging

logger = logging.getLogger(__name__)

@mcp.tool()
def read_file(path: str, full_context: bool = False) -> str:
    """
    Read file content, if you need to read the full content of the file, set full_context to true, otherwise return the first 8000 characters of the file.
    """
    if path.lower().endswith(('.xlsx', '.xls')):  ##xlsx是二进制文件，不能用文本模式读取
        return path

    with open(path, "r") as f:
        result = f.read()
        if len(result) > 8000 and not full_context:
            return result[:8000] + f"... (truncated, {len(result[8000:])} more bytes remaining)"
        else:
            return result

@mcp.tool()
def read_file_with_line_numbers(path: str, start_line: int = 1, end_line: int = None) -> str:
    """
    Read file content with line numbers displayed.
    
    Args:
        path (str): The path of the file to read
        start_line (int): Starting line number to read (1-based, default: 1)
        end_line (int): Ending line number to read (1-based, inclusive, default: None for all lines)
    
    Returns:
        str: File content with line numbers in format "LINE_NUMBER→LINE_CONTENT"
    """
    if path.lower().endswith(('.xlsx', '.xls')):
        return f"error: {path} is a binary file, cannot read as text"
    
    if not os.path.exists(path):
        return f"error: file not found: {path}"
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # Validate line numbers
        if start_line < 1:
            return "error: start_line must be greater than 0"
        
        if end_line is not None and end_line < start_line:
            return "error: end_line must be greater than or equal to start_line"
        
        if start_line > total_lines:
            return f"error: start_line ({start_line}) exceeds total lines ({total_lines})"
        
        # Set end_line to total_lines if not specified
        if end_line is None:
            end_line = total_lines
        elif end_line > total_lines:
            end_line = total_lines
        
        # Extract the specified range (convert to 0-based index)
        start_idx = start_line - 1
        end_idx = end_line - 1
        selected_lines = lines[start_idx:end_idx + 1]
        
        # Format with line numbers
        result_lines = []
        for i, line in enumerate(selected_lines, start=start_line):
            # Remove trailing newline for formatting, then add it back
            line_content = line.rstrip('\n')
            result_lines.append(f"{i:6d}→{line_content}")
        
        result = '\n'.join(result_lines)

        return result
        
    except Exception as e:
        return f"error reading file: {str(e)}"

@mcp.tool()
async def write_file(path: str, content: str, context: Context) -> str:
    """
    Write file content. Content must be a plan-text string.
    """
    # 获取文件所在目录
    directory = os.path.dirname(path)
    # 如果目录不存在，则创建目录
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    with open(path, "w") as f:
        f.write(content)
    return f"write file success"

@mcp.tool()
def list_files(path: str, context: Context = None) -> str:
    """
    List files in directory
    """
    if not os.path.exists(path):
        return "result: no files found"
    res = os.listdir(path)    
    if len(res) == 0:
        return "result: no files found"
    else:
        return "result:\n" + "\n".join(res)

@mcp.tool()
def read_file_for_excel(path: str) -> str:
    """
    Read file content. 
    If the file is an Excel or CSV file, it will return the first 30 rows of data and some basic information.
    If the file is a text file, it will return the first 100,000 characters of the file.
    
    Args:
        path (str): The path of the file to read.
    """
    if path.lower().endswith(('.xlsx', '.xls', '.csv')):  ##xlsx是二进制文件，不能用文本模式读取. 表格数据仅显示基础信息
        try:
            import pandas as pd
            ## 根据文件类型选择不同的读取方式
            if path.lower().endswith(('.xlsx', '.xls')):
                df = pd.read_excel(path)
            else:
                df = pd.read_csv(path, encoding='utf-8')

            # 提取基础信息
            info = f"file: {path}\n"
            info += f"rows: {df.shape[0]}, columns: {df.shape[1]}\n"
            info += f"headers: {list(df.columns)}\n"
            info += f"\nFirst 30 rows (values only):\n{df.head(30).values.tolist()}\n"
            return info
        except Exception as e:
             return f"read file error: {str(e)}"
    else:
        with open(path, "r") as f:
            result = f.read()
            if len(result) > 100_000:
                return result[:100_000] + f"... (truncated, {len(result[100_000:])} more bytes remaining)"
            else:
                return result

@mcp.tool()
def list_files_for_excel(path: str) -> str:
    """
    List files in directory

    Args:
        path (str): Files can only be stored in /workspace or /workspace/uploaded_files directory.
    Returns:
        str: The results of directory listing.
    """
    if not os.path.exists(path):
        return "result: no files found"
    res = os.listdir(path)
    # 过滤掉以 _clean.csv 和 _analysis.csv 结尾的文件
    filtered_res = [file for file in res if not file.endswith(('_original.csv', '_cleaned.csv', '_analysis.csv', '.py', 'collected_data_from_web.csv', 'reference_url.md', '_final.xlsx', '_tmp.xlsx'))]
    if len(filtered_res) == 0:
        return "result: no files found"
    else:
        return "result:\n" + "\n".join(filtered_res)

@mcp.tool()
def append_file(path: str, content: str) -> str:
    """
    Append file content
    """
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)
        if not content.endswith("\n"):
            f.write("\n")
    return f"append file success"

@mcp.tool()
def delete_file(path: str) -> str:
    """
    Delete file
    """
    os.remove(path)
    return f"delete file success"

@mcp.tool()
def move_file(src_path: str, dst_path: str) -> str:
    """
    Move file
    """
    shutil.move(src_path, dst_path)
    return f"move file success"

@mcp.tool()
def copy_file(src_path: str, dst_path: str) -> str:
    """
    Copy file
    """
    shutil.copy(src_path, dst_path)
    return f"copy file success"

@mcp.tool()
def head_file(path: str, n: int) -> str:
    """
    Read first n lines of file
    """
    with open(path, "r") as f:
        return "\n".join(f.readlines()[:n])

@mcp.tool()
def tail_file(path: str, n: int) -> str:
    """
    Read last n lines of file
    """
    with open(path, "r") as f:
        return f.readlines()[-n:]

def transform_image_to_binary(path: str) -> tuple[bytes, str]:
    # 判断是否为URL
    if urlparse(path).scheme in ['http', 'https']:
        # 从网络获取图片
        response = requests.get(path, timeout=60)
        response.raise_for_status()  # 检查请求是否成功
        image_data = response.content
    else:
        # 从本地读取图片
        if not os.path.exists(path):
            raise FileNotFoundError(f"Image file not found: {path}")
        with open(path, 'rb') as image_file:
            image_data = image_file.read()
    image_format = detect_image_format(image_data)
    return image_data, image_format


def detect_image_format(byte_data: bytes) -> Optional[str]:
    if byte_data.startswith(b'\x89PNG\r\n\x1a\n'):
        return "png"
    elif byte_data[:3] == b'\xFF\xD8\xFF':
        return "jpeg"
    elif byte_data.startswith((b'GIF87a', b'GIF89a')):
        return "gif"
    elif byte_data[:4] == b'RIFF' and byte_data[8:12] == b'WEBP':
        return "webp"
    else:
        return "png" # 默认返回png

@mcp.tool()
def read_image(path: str) -> Optional[str | Image]:
    """
    Read image file from local or web. Path can be a local file path or a web url.
    """
    is_valid_image = False
    if os.path.exists(path) and path.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")):
        is_valid_image = True
    if path.startswith(("http://", "https://")):
        is_valid_image = True
    
    if not is_valid_image:
        return f"not an image file: {path}"
    
    try:
        image_data, image_format = transform_image_to_binary(path)
        print(f"image_format: {image_format}")
        return Image(data=image_data, format=image_format)
    except Exception as e:
        return f"unable to read image: {e}"
    
@mcp.tool()
def download_files(urls: list[str] = Field(description="The urls of the files to download."),
                  local_paths: list[str] = Field(description="The local paths to save the files")) -> str:
    """
    Download any type of files (PDF, PPT, images, etc.) from multiple URLs and save it to local paths.
    Supported file types: documents (PDF, DOC, PPT), images (JPG, PNG, GIF, WebP), media (MP3, MP4), archives (ZIP, RAR), software (exe, dmg, app).
    length of urls and local_paths must be the same.
    """
    if len(urls) != len(local_paths):
        return f"the length of urls and local_paths must be the same"
    
    success_count = 0
    failed_count = 0
    success_files = []
    failed_files = []
    for url, local_path in zip(urls, local_paths):
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()  # 检查请求是否成功
            with open(local_path, "wb") as f:
                f.write(response.content)
            success_count += 1
            success_files.append(local_path)
        except Exception as e:
            failed_count += 1
            failed_files.append(local_path)
    return f"download {success_count} files successfully, {failed_count} files failed, success files: {success_files}, failed files: {failed_files}"

def _normalize_content(content: str) -> str:
    """
    Normalize content for comparison by removing trailing whitespace and normalizing line endings.
    """
    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split into lines and remove trailing whitespace from each line
    lines = content.split('\n')
    normalized_lines = [line.rstrip() for line in lines]
    
    # Rejoin with newlines
    result = '\n'.join(normalized_lines)
    
    return result

def _robust_match(content: str, search: str) -> bool:
    """
    Robust content matching that handles common formatting differences.
    """
    # Strategy 1: Exact match
    if content == search:
        return True
    
    # Strategy 2: Normalized match (remove trailing whitespace)
    normalized_content = _normalize_content(content)
    normalized_search = _normalize_content(search)
    if normalized_content == normalized_search:
        return True
    
    # Strategy 3: Strip all whitespace and compare
    if content.strip() == search.strip():
        return True
    
    # Strategy 4: Line-by-line comparison (ignore empty lines and strip each line)
    content_lines = [line.strip() for line in content.split('\n') if line.strip()]
    search_lines = [line.strip() for line in search.split('\n') if line.strip()]
    if content_lines == search_lines:
        return True
    
    # Strategy 5: Check if search is a substring (for partial matches)
    if search.strip() in content:
        return True
    
    # Strategy 6: Check if content is a substring of search
    if content.strip() in search:
        return True
    
    return False

def _match_with_ellipsis(content: str, search_pattern: str) -> bool:
    """
    Match content using ellipsis pattern.
    """
    # Split the search pattern by ellipsis
    parts = search_pattern.split('...')
    
    if len(parts) == 1:
        # No ellipsis, exact match
        return _robust_match(content, search_pattern)
    
    if len(parts) == 2:
        # One ellipsis: prefix...suffix
        prefix, suffix = parts
        normalized_content = _normalize_content(content)
        normalized_prefix = _normalize_content(prefix)
        normalized_suffix = _normalize_content(suffix)
        
        return normalized_content.startswith(normalized_prefix) and normalized_content.endswith(normalized_suffix)
    
    # Multiple ellipsis: check all parts exist in order
    normalized_content = _normalize_content(content)
    current_pos = 0
    
    for part in parts:
        if not part.strip():
            continue
        normalized_part = _normalize_content(part)
        pos = normalized_content.find(normalized_part, current_pos)
        if pos == -1:
            return False
        current_pos = pos + len(normalized_part)
    
    return True

def _find_content_in_file(file_content: str, search: str, lines: list[str]) -> dict[str, any]:
    """
    Find content in the entire file and return the line range.
    """
    # Normalize the search content
    normalized_search = _normalize_content(search)
    
    # Search for the content in the file
    if '...' in search:
        # Handle ellipsis pattern
        parts = search.split('...')
        if len(parts) == 2:
            prefix, suffix = parts
            normalized_prefix = _normalize_content(prefix)
            normalized_suffix = _normalize_content(suffix)
            
            # Find prefix and suffix in the file
            prefix_pos = file_content.find(normalized_prefix)
            if prefix_pos != -1:
                # Find suffix after prefix
                suffix_pos = file_content.find(normalized_suffix, prefix_pos + len(normalized_prefix))
                if suffix_pos != -1:
                    # Calculate line numbers
                    content_before_prefix = file_content[:prefix_pos]
                    content_before_suffix = file_content[:suffix_pos + len(normalized_suffix)]
                    
                    first_line = content_before_prefix.count('\n') + 1
                    last_line = content_before_suffix.count('\n')
                    
                    return {
                        'found': True,
                        'first_line': first_line,
                        'last_line': last_line
                    }
    else:
        # Exact content search
        normalized_file_content = _normalize_content(file_content)
        pos = normalized_file_content.find(normalized_search)
        if pos != -1:
            # Calculate line numbers
            content_before = file_content[:pos]
            content_after = file_content[:pos + len(search)]
            
            first_line = content_before.count('\n') + 1
            last_line = content_after.count('\n')
            
            return {
                'found': True,
                'first_line': first_line,
                'last_line': last_line
            }
    
    return {'found': False}

def _perform_search_replace(file_path: str, search: str, replace: str, lines: list[str]) -> dict[str, any]:
    """
    Perform search and replace operation on the file content.
    """
    try:
        # Convert lines back to content
        content = ''.join(lines)
        total_lines_before = len(lines)
        
        # Perform the replacement
        new_content = content.replace(search, replace)
        replacements_made = content.count(search)
        
        # Check if any replacements were made
        if replacements_made == 0:
            error_msg = f"Search content not found in {file_path}"
            return {
                'success': False,
                'error': error_msg,
                'file_path': file_path,
                'search_content': search
            }
        
        # Split new content back to lines
        new_lines = new_content.splitlines(keepends=True)
        if not new_lines and new_content:
            # If content is not empty but splitlines returned empty, add a newline
            new_lines = [new_content + '\n']
        
        # Write the file back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        # Calculate statistics
        total_lines_after = len(new_lines)
        lines_changed = total_lines_after - total_lines_before
                
        return {
            'success': True,
            'file_path': file_path,
            'replacements_made': replacements_made,
            'lines_changed': lines_changed,
            'total_lines_before': total_lines_before,
            'total_lines_after': total_lines_after,
            'message': f'Successfully made {replacements_made} replacement(s) using search_replace fallback',
            'method': 'search_replace_fallback'
        }
        
    except Exception as e:
        error_msg = f"Error performing search_replace fallback: {str(e)}"
        return {
            'success': False,
            'error': error_msg,
            'file_path': file_path
        }

@mcp.tool()
def write_file_search_replace(
    file_path: str,
    search: str,
    first_replaced_line: int,
    last_replaced_line: int,
    replace: str
) -> str:
    """
    This tool is used to partially modify files using explicit line numbers: it allows line-based search and replacement of file contents. This is the PREFERRED and PRIMARY tool for editing existing files. Always use this tool when modifying existing code rather than rewriting entire files. 
    ELLIPSIS USAGE: When replacing sections of code longer than ~6 lines, you should use ellipsis (...) in your search to reduce the number of lines you need to specify (writing fewer lines is faster).
        - Include the first few lines (typically 2-3 lines) of the section you want to replace
        - Add \"...\" on its own line to indicate omitted content
        - Include the last few lines (typically 2-3 lines) of the section you want to replace
        - The key is to provide enough unique context at the beginning and end to ensure accurate matching
        - Focus on uniqueness rather than exact line counts - sometimes 2 lines is enough, sometimes you need 4

    Args:
        file_path (str): file path
        search (str): Content to search for in the file (without line numbers). This should match the existing code that will be replaced.
        first_replaced_line (int): First line number to replace (1-indexed)
        last_replaced_line (int): Last line number to replace (1-indexed)
        replace (str): New content to replace the found content(without line numbers)
        
    Returns:
        str: JSON formatted result with success status and details
    """
    try:        
        # Check if file exists
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            result = {
                'success': False,
                'error': error_msg,
                'file_path': file_path
            }
            return str(result)
        
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # Validate line numbers
        if first_replaced_line < 1 or last_replaced_line > total_lines:
            error_msg = f"Line numbers out of range. File has {total_lines} lines, requested range: {first_replaced_line}-{last_replaced_line}"
            result = {
                'success': False,
                'error': error_msg,
                'file_path': file_path,
                'total_lines': total_lines,
                'requested_range': f"{first_replaced_line}-{last_replaced_line}"
            }
            return str(result)
        
        if first_replaced_line > last_replaced_line:
            error_msg = f"Invalid line range: first line ({first_replaced_line}) must be <= last line ({last_replaced_line})"
            result = {
                'success': False,
                'error': error_msg,
                'file_path': file_path
            }
            return str(result)
        
        # Extract the content from the specified line range
        start_idx = first_replaced_line - 1  # Convert to 0-based indexing
        end_idx = last_replaced_line
        original_content = ''.join(lines[start_idx:end_idx])
        
        # Validate search content matches the actual file content
        # Handle ellipsis in search pattern
        if '...' in search:
            search_matches = _match_with_ellipsis(original_content, search)
        else:
            # For exact content validation, use robust matching
            search_matches = _robust_match(original_content, search)
        
        if not search_matches:
            # Try search_replace as fallback
            logger.info(f"Content not found at lines {first_replaced_line}-{last_replaced_line}, trying search_replace fallback...")
            
            # Try to find the content in the entire file
            file_content = ''.join(lines)
            search_result = _find_content_in_file(file_content, search, lines)
            
            if search_result['found']:
                adjusted_first_line = search_result['first_line']
                adjusted_last_line = search_result['last_line']
                logger.info(f"Found content at lines {adjusted_first_line}-{adjusted_last_line}, performing search_replace")
                
                # Perform search_replace
                fallback_result = _perform_search_replace(file_path, search, replace, lines)
                return str(fallback_result)
            else:
                # Provide detailed error information
                error_msg = f"Search content does not match the content at lines {first_replaced_line}-{last_replaced_line} and not found elsewhere in file"
                result = {
                    'success': False,
                    'error': error_msg,
                    'file_path': file_path,
                    'expected_content': search,
                    'actual_content': original_content,
                    'line_range': f"{first_replaced_line}-{last_replaced_line}",
                    'actual_lines': [f"{i:4d}: {line.rstrip()}" for i, line in enumerate(lines[start_idx:end_idx], first_replaced_line)]
                }
                return str(result)
        
        # Split the replacement content into lines
        replacement_lines = replace.splitlines(keepends=True)
        if not replacement_lines and replace:
            # If replace is not empty but splitlines returned empty, add a newline
            replacement_lines = [replace + '\n']
        
        # Perform the replacement
        new_lines = lines[:start_idx] + replacement_lines + lines[end_idx:]
        
        # Write the file back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        # Calculate statistics
        lines_removed = last_replaced_line - first_replaced_line + 1
        lines_added = len(replacement_lines)
        new_total_lines = len(new_lines)
                
        result = {
            'success': True,
            'file_path': file_path,
            'line_range': f"{first_replaced_line}-{last_replaced_line}",
            'lines_removed': lines_removed,
            'lines_added': lines_added,
            'total_lines_before': total_lines,
            'total_lines_after': new_total_lines,
            'message': f'Successfully replaced {lines_removed} lines with {lines_added} lines'
        }
        return str(result)

    except Exception as e:
        error_msg = f"Error performing line replace: {str(e)}"
        result = {
            'success': False,
            'error': error_msg,
            'file_path': file_path
        }
        return str(result)

if __name__ == "__main__":
    print(download_files(urls=
                         ["https://mmbiz.qpic.cn/mmbiz_jpg/FhEbElLWONKs6dRXJDH43CmE5PMXa2soJYnWovhHiaOquDMWNOe0ibagzzOJVYzy746uDOjdGndqUAaYCAcEfCHg/640?wx_fmt=jpeg&from=appmsg&tp=webp&wxfrom=5&wx_lazy=1&wx_co=1", 
                          "https://arxiv.org/pdf/2504.07558", 
                          "https://download.typora.io/mac/Typora.dmg"], 
                        local_paths=["test.jpg", "test.pdf", "Typora.dmg"]))
