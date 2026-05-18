"""
One-time script to fix the batch extraction block indentation in app.py.
Run this once from the backend directory: python fix_indentation.py
"""

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# We identify the broken section by two stable anchors
START = (
    "# REMOVED: Early exit on signature. We now try extraction regardless \n"
    "                          # in case the signature was slightly mangled but the data is there."
)
END = 'zf.writestr("DEEPSTEGAI_BATCH_REPORT.txt", "\\n".join(summary_lines))'

if START not in content:
    # Try without extra leading spaces variant
    START = (
        "# REMOVED: Early exit on signature. We now try extraction regardless \r\n"
        "                          # in case the signature was slightly mangled but the data is there."
    )

start_idx = content.find(START)
end_idx = content.find(END)

if start_idx == -1 or end_idx == -1:
    print(f"FAILED: Could not find start_idx={start_idx}, end_idx={end_idx}")
else:
    NEW_BLOCK = """\
# REMOVED: Early exit on signature. We now try extraction regardless 
                          # in case the signature was slightly mangled but the data is there.
                          summary_lines.append(f"[*] Analyzing {stego_file.filename} (Scan hint: {scan_res['message']})")

                          # 2. Key Trial Loop
                          for key in candidate_keys:
                              try:
                                  raw_block = b""

                                  # ENGINE 1: Try Adaptive
                                  try:
                                      _, raw_block, _ = extract_file_adaptive(s_img, password=key)
                                  except:
                                      if len(key) >= 16:
                                          try:
                                              _, raw_block, _ = extract_file_adaptive(s_img, recovery_token=key)
                                          except:
                                              pass

                                  # ENGINE 2: Try LSB
                                  if not raw_block:
                                      try:
                                          _, raw_block, _ = extract_payload_from_image(s_img)
                                      except:
                                          pass

                                  if raw_block:
                                      try:
                                          is_tok = len(key) >= 16 and "-" in key
                                          res_files, is_bundle_val = unpackage_payload(
                                              raw_block,
                                              password=None if is_tok else key,
                                              recovery_token=key if is_tok else None
                                          )
                                          if is_bundle_val:
                                              for rf in res_files:
                                                  zf.writestr(f"{i}_{rf['name']}", rf['data'])
                                          else:
                                              zf.writestr(f"{i}_{res_files[0]['name']}", res_files[0]['data'])

                                          summary_lines.append(f"  [+] Success using key: '{key[:5]}...'")
                                          processed_success += 1
                                          success_for_this_file = True
                                          break
                                      except:
                                          pass
                              except Exception as e:
                                  last_error = str(e)
                                  continue

                          if not success_for_this_file:
                              summary_lines.append(f"  [-] Failed. Last tried key error hint: {last_error}")

                      except Exception as e:
                          summary_lines.append(f"  [-] Critical Error: {str(e)}")
                          logger.error(f"Batch extractor critical failure: {e}")
                 
                  """

    new_content = content[:start_idx] + NEW_BLOCK + content[end_idx:]
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("SUCCESS: Indentation fixed in app.py")
