"""
AI Memory OS — Folder & File Ingestion Page (Tenant-Scoped)
Primary feature: Ingest any parent folder with arbitrary nested subfolders (folder inside folder inside folder).
Includes recursion protection to prevent copying a folder into itself.
"""

import os
import shutil
import streamlit as st
from pathlib import Path
from auth import get_user_data_dir

ROOT_DIR = Path(__file__).parent.parent

# ─── Page content ─────────────────────────────────────────────────────
username = st.session_state.username

st.caption("Provide a parent folder path to automatically index all files across any depth of nested subfolders.")

# ─── Tab 1: Parent Folder (Primary) | Tab 2: File Upload ───────────────
tab_folder, tab_upload = st.tabs([
    ":material/folder_open: Ingest Parent Folder (Nested Subfolders)",
    ":material/upload_file: Upload Individual Files",
])

# ═══════════════════════════════════════════════════════════════════════
# TAB 1: Parent Folder (Deeply Nested Subfolders Support)
# ═══════════════════════════════════════════════════════════════════════
with tab_folder:
    st.subheader(":material/create_new_folder: Parent Folder Selection")
    st.markdown(
        "Enter the **absolute path** of your parent folder. "
        "The system will automatically traverse **all nested subdirectories** "
        "(`parent/subfolder_level_1/subfolder_level_2/.../file.ext`) and extract memories."
    )

    folder_path = st.text_input(
        "Parent folder path",
        placeholder="/home/shashank/local-RAG/data/user1",
        key="folder_path_input",
    )

    col_copy, col_info = st.columns([1, 2])
    with col_copy:
        copy_files = st.checkbox(
            "Copy folder structure into vault",
            value=True,
            help="If checked, external files are copied into your user data directory (`data/<username>/`). "
                 "If unchecked, files are indexed directly in-place from the source folder.",
        )

    if folder_path:
        source_dir = Path(folder_path.strip()).resolve()
        user_data_dir = get_user_data_dir(username).resolve()

        if not source_dir.exists():
            st.error(f"Path does not exist: `{source_dir}`", icon=":material/error:")
        elif not source_dir.is_dir():
            st.error("Provided path is a file, not a directory. Please provide a parent folder path.", icon=":material/error:")
        else:
            from ingest import count_files_fast, discover_files

            # Detect if source_dir IS the user vault or inside/outside it
            is_same_or_inside_vault = (
                source_dir == user_data_dir
                or user_data_dir in source_dir.parents
                or source_dir in user_data_dir.parents
            )

            if is_same_or_inside_vault and copy_files:
                st.info(
                    "💡 The selected folder is already inside or overlaps with your vault (`data/user1`). "
                    "In-place indexing will be used automatically to prevent duplicate copying.",
                    icon=":material/info:",
                )
                should_copy = False
            else:
                should_copy = copy_files

            # Quick scan of nested subfolders
            file_count = count_files_fast(source_dir)

            if file_count == 0:
                st.warning(
                    f"No supported files found in `{source_dir}` or any of its subfolders.",
                    icon=":material/search_off:"
                )
            else:
                # Count distinct subdirectories containing files
                subdirs = set()
                sample_files = []
                for idx, f in enumerate(discover_files(source_dir)):
                    try:
                        rel_p = f.relative_to(source_dir)
                    except ValueError:
                        rel_p = f.name
                    subdirs.add(str(rel_p.parent) if hasattr(rel_p, "parent") else "")
                    if idx < 5:
                        sample_files.append(str(rel_p))

                st.success(
                    f"Discovered **{file_count:,}** supported files across **{len(subdirs):,}** folder level(s) in `{source_dir.name}`!",
                    icon=":material/folder_zip:",
                )

                with st.expander(":material/account_tree: Folder Tree Preview (Sample Files)", expanded=False):
                    for sample in sample_files:
                        st.caption(f"📁 `{source_dir.name}/{sample}`")
                    if file_count > 5:
                        st.caption(f"... and {file_count - 5:,} more nested files")

                if st.button(
                    f":material/rocket_launch: Ingest Entire Folder Tree ({file_count:,} files)",
                    type="primary",
                    key="folder_ingest_btn",
                ):
                    # Copy files if requested and safe
                    if should_copy:
                        copy_progress = st.progress(0, text="Copying nested folder tree into vault...")
                        copied = 0
                        for filepath in discover_files(source_dir):
                            try:
                                rel = filepath.relative_to(source_dir)
                            except ValueError:
                                rel = filepath.name
                            dest = user_data_dir / rel
                            # Recursion protection check
                            if dest.resolve() != filepath.resolve():
                                dest.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(str(filepath), str(dest))
                                copied += 1
                                if copied % 50 == 0 or copied == file_count:
                                    copy_progress.progress(
                                        min(copied / file_count, 1.0),
                                        text=f"Copied {copied:,}/{file_count:,} files...",
                                    )
                        copy_progress.progress(1.0, text=f"Folder tree copied ({copied:,} files).")
                        ingest_target_dir = user_data_dir
                    else:
                        ingest_target_dir = source_dir

                    # Run ingestion with streaming progress callback
                    ingest_progress = st.progress(0, text="Indexing files across all nested subfolders...")

                    def folder_progress_cb(done, total, current_file):
                        if total > 0:
                            ingest_progress.progress(
                                min(done / total, 1.0),
                                text=f"Processing {done:,}/{total:,}: {current_file}",
                            )

                    from ingest import ingest
                    stats = ingest(
                        data_dir=ingest_target_dir,
                        show_progress=False,
                        tenant_id=username,
                        progress_callback=folder_progress_cb,
                    )

                    ingest_progress.progress(1.0, text="Ingestion complete!")

                    st.success(
                        f"Successfully indexed **{stats['files_processed']:,}** files across nested folders → "
                        f"**{stats['chunks_created']:,}** memory chunks generated!",
                        icon=":material/check_circle:",
                    )

                    if stats.get("files_skipped", 0) > 0:
                        st.info(f"{stats['files_skipped']:,} file(s) skipped (empty or no extractable text)")

                    if stats.get("errors"):
                        with st.expander(f":material/warning: Warnings ({len(stats['errors'])})", expanded=False):
                            for err in stats["errors"][:50]:
                                st.caption(f"• {err}")
                            if len(stats["errors"]) > 50:
                                st.caption(f"... and {len(stats['errors']) - 50} more")

# ═══════════════════════════════════════════════════════════════════════
# TAB 2: Upload Individual Files
# ═══════════════════════════════════════════════════════════════════════
with tab_upload:
    st.subheader(":material/upload: Upload Files")
    uploaded_files = st.file_uploader(
        "Upload files directly to add to your knowledge vault",
        accept_multiple_files=True,
        type=["txt", "pdf", "docx", "pptx", "xlsx", "xls", "csv", "md",
              "json", "xml", "html", "png", "jpg", "jpeg", "bmp"],
        label_visibility="collapsed",
    )

    if uploaded_files:
        st.info(
            f"{len(uploaded_files)} file(s) selected. Click below to process and index them.",
            icon=":material/upload_file:",
        )

        if st.button(":material/rocket_launch: Start Ingestion", type="primary", key="upload_ingest_btn"):
            user_data_dir = get_user_data_dir(username)

            progress_bar = st.progress(0, text="Saving uploaded files...")

            saved_count = 0
            for f in uploaded_files:
                target_path = user_data_dir / f.name
                with open(target_path, "wb") as out_file:
                    out_file.write(f.read())
                saved_count += 1
                progress_bar.progress(
                    saved_count / len(uploaded_files),
                    text=f"Saved {saved_count}/{len(uploaded_files)} files...",
                )

            progress_bar.progress(0, text="Indexing files into memory...")

            def progress_cb(done, total, current_file):
                if total > 0:
                    progress_bar.progress(
                        min(done / total, 1.0),
                        text=f"Processing {done:,}/{total:,}: {current_file}",
                    )

            from ingest import ingest
            stats = ingest(
                data_dir=user_data_dir,
                show_progress=False,
                tenant_id=username,
                progress_callback=progress_cb,
            )

            progress_bar.progress(1.0, text="Complete!")

            st.success(
                f"Processed {stats['files_processed']:,} files → "
                f"{stats['chunks_created']:,} memory chunks indexed!",
                icon=":material/check_circle:",
            )

            if stats.get("errors"):
                with st.expander(f":material/warning: Warnings ({len(stats['errors'])})", expanded=False):
                    for err in stats["errors"][:50]:
                        st.caption(f"• {err}")
    else:
        st.caption("Supported file extensions: PDF, DOCX, XLSX, XLS, CSV, PPTX, TXT, MD, JSON, XML, HTML, PNG, JPG, BMP")
