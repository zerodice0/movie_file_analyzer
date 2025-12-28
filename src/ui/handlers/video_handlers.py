"""비디오 로드 및 히스토리 관련 핸들러."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QListWidgetItem, QMessageBox


class VideoHandlerMixin:
    """비디오 로드 및 히스토리 관련 핸들러 믹스인."""

    def _on_browse_clicked(self):
        """파일 선택 버튼 클릭."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "영상 파일 선택", "",
            "영상 파일 (*.mp4 *.mkv *.avi *.mov *.webm);;모든 파일 (*)",
        )
        if file_path:
            self._load_video(Path(file_path))

    def _load_video(self, video_path: Path):
        """영상 파일을 로드합니다."""
        try:
            self.video_info = self.frame_extractor.get_video_info(video_path)
            self.video_path = video_path

            self.file_panel.set_video_info(
                video_path,
                self.video_info.duration_str,
                self.video_info.width,
                self.video_info.height,
                self.video_info.size_mb,
            )

            self._update_strategy_list()
            self.settings_panel.set_analyze_enabled(True)

            # 기존 분석 결과 확인
            if self.metadata_store.has_sidecar(video_path):
                existing = self.metadata_store.load_sidecar(video_path)
                if existing:
                    reply = QMessageBox.question(
                        self, "기존 분석 결과",
                        f"이 영상의 분석 결과가 이미 있습니다.\n"
                        f"({existing.created_at[:10]}, {existing.ai_provider})\n\n"
                        "기존 결과를 불러오시겠습니까?",
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    if reply == QMessageBox.Yes:
                        self.result_panel.set_result(existing.analysis_result)
                        self.result_panel.set_buttons_enabled(copy=True)

        except Exception as e:
            QMessageBox.critical(self, "오류", f"영상을 로드할 수 없습니다:\n{e}")

    def _load_history(self):
        """히스토리를 로드합니다."""
        self.history_panel.clear()

        try:
            records = self.metadata_store.list_history(limit=50)

            if not records:
                self.history_panel.show_empty()
                return

            for record in records:
                date_str = record.created_at[:10] if record.created_at else "unknown"
                text = f"📹 {record.video_name}\n   {date_str} | {record.ai_provider} | {record.frame_count}장"
                self.history_panel.add_item(text, record.id)

            self.history_panel.show_list()

        except PermissionError as e:
            self.history_panel.show_error(f"파일 접근 권한이 없습니다: {e}")
        except (OSError, IOError) as e:
            self.history_panel.show_error(f"파일 시스템 오류: {e}")
        except Exception as e:
            self.history_panel.show_error(f"알 수 없는 오류: {e}")

    def _on_history_item_clicked(self, item: QListWidgetItem):
        """히스토리 항목 클릭."""
        record_id = item.data(Qt.UserRole)
        record = self.metadata_store.get_from_history(record_id)
        if record:
            self.result_panel.set_result(record.analysis_result)
            self.result_panel.set_buttons_enabled(copy=True)
            self.progress_panel.set_progress(
                100, f"📚 히스토리에서 로드: {record.video_name} ({record.created_at[:10]})"
            )

    def _on_delete_history_clicked(self):
        """히스토리 삭제 버튼 클릭."""
        record_id = self.history_panel.get_selected_record_id()
        if record_id is None:
            QMessageBox.information(self, "알림", "삭제할 항목을 선택하세요.")
            return

        reply = QMessageBox.question(
            self, "삭제 확인", "선택한 분석 기록을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.metadata_store.delete_from_history(record_id)
            self._load_history()
            self.progress_panel.set_progress(100, "🗑️ 히스토리 삭제됨")

    def _on_copy_clicked(self):
        """복사 버튼 클릭."""
        text = self.result_panel.get_result_text()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.progress_panel.set_progress(100, "📋 클립보드에 복사됨")

    def _on_clear_cache_clicked(self):
        """캐시 정리 버튼 클릭."""
        reply = QMessageBox.question(
            self, "캐시 정리", "모든 캐시를 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            count = self.cache_manager.cleanup_all()
            self._update_cache_info()
            self.progress_panel.set_progress(100, f"🗑️ {count}개 캐시 삭제됨")

    def _update_cache_info(self):
        """캐시 정보 업데이트."""
        cache_size = self.cache_manager.get_total_size()
        cache_size_str = self.cache_manager.format_size(cache_size)
        self.result_panel.set_cache_info(cache_size_str)
