def atomic_write(target_path, content, is_bytes=False):
    dirname = os.path.dirname(target_path)
    mode = "wb" if is_bytes else "w"
    with tempfile.NamedTemporaryFile(mode, dir=dirname, delete=False) as tf:
        tf.write(content)
        temp_name = tf.name
    os.replace(temp_name, target_path)
