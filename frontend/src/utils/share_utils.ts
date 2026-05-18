/**
 * Converts a base64 data URL (e.g., "data:image/png;base64,...") into a File object.
 * This is necessary for the Web Share API, which requires File/Blob objects.
 */
export function base64ToFile(dataUrl: string, filename: string): File {
  const [header, base64Data] = dataUrl.split(',')
  const mimeType = header.match(/:(.*?);/)?.[1] ?? 'image/png'
  const binary = atob(base64Data)
  const buffer = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    buffer[i] = binary.charCodeAt(i)
  }
  return new File([buffer], filename, { type: mimeType })
}

/**
 * Shares a file using the Web Share API.
 * Returns true on success, false if not supported or cancelled.
 */
export async function shareFile(
  file: File,
  title: string,
  text: string,
): Promise<boolean> {
  if (!navigator.share || !navigator.canShare?.({ files: [file] })) {
    return false
  }
  try {
    await navigator.share({ files: [file], title, text })
    return true
  } catch (err: any) {
    // AbortError means the user cancelled — not a real error
    if (err?.name !== 'AbortError') {
      console.error('Share failed:', err)
    }
    return false
  }
}
