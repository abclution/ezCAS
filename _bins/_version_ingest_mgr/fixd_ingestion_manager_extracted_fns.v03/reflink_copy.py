def reflink_copy(src: Path, dst: Path) -> bool:
    """Performs a CoW reflink copy. Returns True on success."""
    src = src.resolve()
    dst = dst.resolve()
    
    # 1. macOS clonefile
    if hasattr(os, 'clonefile'):
        try:
            if dst.exists():
                os.unlink(dst)
            os.clonefile(src, dst)
            return True
        except OSError as e:
            print(f"  [Error] clonefile failed: {e}", file=sys.stderr)
            return False

    # 2. Linux ioctl FICLONE (0x40049409)
    if platform.system() == 'Linux':
        try:
            FICLONE = 0x40049409
            if dst.exists():
                os.unlink(dst)
            # We must open dst in write mode to create it, then clone
            with open(src, 'rb') as s_file, open(dst, 'wb') as d_file:
                import fcntl
                fcntl.ioctl(d_file.fileno(), FICLONE, s_file.fileno())
            return True
        except Exception:
            # Fallback to cp command if ioctl fails or fcntl missing
            pass

    # 3. CLI Fallback (cp --reflink=always)
    try:
        if dst.exists():
            os.unlink(dst)
        subprocess.run(
            ['cp', '--reflink=always', str(src), str(dst)], 
            check=True, 
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError:
        return False
