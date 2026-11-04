import os
from dotenv import load_dotenv

load_dotenv()
from pathlib import Path
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from kivy.clock import Clock

from kivy.uix.screenmanager import ScreenManager, Screen

from meetnote.application.services import MeetingService
from meetnote.application.transcription import (
    FakeTranscriber,
    LocalWhisperTranscriber,
)
from meetnote.application.ai import (
    FakeActionItemExtractor,
    GeminiActionItemExtractor,
)


class MeetingScreen(Screen):
    def __init__(
        self,
        meeting_service: MeetingService,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        self.meeting_service = meeting_service

        scroll = ScrollView()

        layout = BoxLayout(
            orientation="vertical",
            spacing=10,
            padding=20,
            size_hint_y=None,
        )
        layout.bind(minimum_height=layout.setter("height"))

        scroll.add_widget(layout)
        self.add_widget(scroll)

        self.executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="meetnote-worker",
        )
        self.is_shutting_down = False
        self.transcription_future: Future[str] | None = None
        self.extraction_future: Future[int] | None = None
        self.summary_future: Future[str] | None = None
        data_directory = Path("data")
        data_directory.mkdir(parents=True, exist_ok=True)

        self.current_meeting_id: int | None = None
        self.selected_file_path: Path | None = None

        self.title_input = TextInput(
            hint_text="Enter meeting title",
            multiline=False,
            size_hint_y=None,
            height=45,
        )

        self.selected_file_label = Label(
            text="No audio or video file selected",
            size_hint_y=None,
            height=40,
        )

        self.status_label = Label(
            text="Status: waiting for a file",
            size_hint_y=None,
            height=40,
        )
        self.transcript_label = Label(
            text="No transcript available",
            halign="left",
            valign="top",
            size_hint_y=None,
            height=120,
        )

        self.meeting_summary_label = Label(
            text="No meeting summary available",
            halign="left",
            valign="top",
            size_hint_y=None,
            height=150,
        )
        self.meeting_summary_label.bind(
            width=self._update_meeting_summary_text_size,
        )
        self.transcript_label.bind(
            width=self._update_transcript_text_size,
        )

        select_file_button = Button(
            text="Select audio or video file",
            size_hint_y=None,
            height=50,
        )
        select_file_button.bind(on_press=self.open_file_chooser)

        self.submit_button = Button(
            text="Submit meeting",
            size_hint_y=None,
            height=50,
        )
        self.submit_button.disabled = False
        self.submit_button.bind(on_press=self.submit_meeting)

        extract_button = Button(
            text="Extract action items",
            size_hint_y=None,
            height=50,
        )
        extract_button.bind(on_press=self.extract_action_items)

        summary_button = Button(
            text="Generate meeting summary",
            size_hint_y=None,
            height=50,
        )
        summary_button.bind(on_press=self.generate_meeting_summary)

        refresh_button = Button(
            text="Refresh action items",
            size_hint_y=None,
            height=50,
        )
        refresh_button.bind(on_press=self.refresh_action_items)

        kanban_button = Button(
            text="Open Kanban board",
            size_hint_y=None,
            height=50,
        )
        kanban_button.bind(on_press=self.open_kanban_board)

        self.action_items_label = Label(
            text="No action items loaded",
            halign="left",
            valign="top",
            size_hint_y=None,
            height=120,
        )
        self.action_items_label.bind(
            width=self._update_action_items_text_size,
        )

        layout.add_widget(
            Label(
                text="MeetNote",
                font_size="30sp",
                size_hint_y=None,
                height=50,
            )
        )
        layout.add_widget(
            Label(
                text="Create a new meeting",
                size_hint_y=None,
                height=35,
            )
        )
        layout.add_widget(self.title_input)
        layout.add_widget(select_file_button)
        layout.add_widget(self.selected_file_label)
        layout.add_widget(self.submit_button)
        layout.add_widget(extract_button)
        layout.add_widget(refresh_button)
        layout.add_widget(kanban_button)
        layout.add_widget(self.transcript_label)
        layout.add_widget(summary_button)
        layout.add_widget(self.meeting_summary_label)
        layout.add_widget(self.action_items_label)
        layout.add_widget(self.status_label)

    def _update_action_items_text_size(
        self,
        label: Label,
        width: float,
    ) -> None:
        label.text_size = (width, None)

    def _update_transcript_text_size(
        self,
        label: Label,
        width: float,
    ) -> None:
        label.text_size = (width, None)

    def open_file_chooser(self, _button: Button) -> None:
        chooser = FileChooserListView(
            path=str(Path.home()),
            filters=[
                "*.mp3",
                "*.wav",
                "*.m4a",
                "*.mp4",
                "*.mov",
                "*.avi",
                "*.flac",
                "*.ogg",
            ],
        )

        choose_button = Button(
            text="Use selected file",
            size_hint_y=None,
            height=50,
        )

        layout = BoxLayout(orientation="vertical")
        layout.add_widget(chooser)
        layout.add_widget(choose_button)

        popup = Popup(
            title="Choose meeting recording",
            content=layout,
            size_hint=(0.9, 0.9),
        )

        choose_button.bind(
            on_press=lambda _button: self.select_file(
                chooser,
                popup,
            )
        )

        popup.open()

    def select_file(
        self,
        chooser: FileChooserListView,
        popup: Popup,
    ) -> None:
        if not chooser.selection:
            self.status_label.text = "Status: select a file first"
            return

        selected_file_path = Path(chooser.selection[0])

        if not selected_file_path.is_file():
            self.status_label.text = "Status: select a file, not a folder"
            return

        self.selected_file_path = selected_file_path
        self.selected_file_label.text = str(selected_file_path)
        self.status_label.text = "Status: file selected"
        popup.dismiss()

    def submit_meeting(self, _button: Button) -> None:
        self.status_label.text = "Status: submit clicked"

        title = self.title_input.text.strip()

        if not title:
            self.status_label.text = "Status: enter a meeting title"
            return

        if self.selected_file_path is None:
            self.status_label.text = "Status: select an audio or video file"
            return

        if (
            self.transcription_future is not None
            and not self.transcription_future.done()
        ):
            self.status_label.text = "Status: transcription already in progress"
            return

        try:
            self.current_meeting_id = self.meeting_service.create_meeting(
                title=title,
                notes=str(self.selected_file_path),
            )
        except Exception as error:
            self.status_label.text = f"Status: submit failed: {error}"
            return

        self.status_label.text = "Status: transcribing recording"
        self.transcript_label.text = "Transcribing..."
        self.action_items_label.text = "No action items loaded"
        self.submit_button.disabled = True

        self.transcription_future = self.executor.submit(
            self.meeting_service.transcribe_meeting,
            self.current_meeting_id,
            self.selected_file_path,
        )
        self.transcription_future.add_done_callback(
            self._transcription_finished,
        )

    def _transcription_finished(
        self,
        future: Future[str],
    ) -> None:
        if self.is_shutting_down:
            return

        Clock.schedule_once(
            lambda _dt: self._show_transcription_result(future),
        )

    def _show_transcription_result(
        self,
        future: Future[str],
    ) -> None:
        if self.is_shutting_down:
            return

        self.submit_button.disabled = False

        try:
            transcript = future.result()
        except Exception as error:
            self.status_label.text = f"Status: transcription failed: {error}"
            return

        self.status_label.text = (
            "Status: meeting submitted; "
            f"transcript length: {len(transcript)} characters"
        )

        self.transcript_label.text = transcript
        self.action_items_label.text = "No action items loaded"
        self.status_label.text = (
            f"Status: meeting submitted (ID {self.current_meeting_id})"
        )

    def open_kanban_board(self, _button: Button) -> None:
        manager = self.parent

        if not isinstance(manager, ScreenManager):
            return

        kanban_screen = manager.get_screen("kanban")

        if not isinstance(kanban_screen, KanbanScreen):
            return

        kanban_screen.current_meeting_id = self.current_meeting_id
        kanban_screen.refresh_board(None)
        manager.current = "kanban"

    def extract_action_items(self, _button: Button) -> None:
        if self.current_meeting_id is None:
            self.action_items_label.text = (
                "Submit a meeting before extracting action items"
            )
            return

        if (
            self.transcription_future is not None
            and not self.transcription_future.done()
        ):
            self.status_label.text = "Status: transcription is still in progress"
            return

        if self.extraction_future is not None and not self.extraction_future.done():
            self.status_label.text = "Status: extraction already in progress"
            return

        meeting_id = self.current_meeting_id
        self.status_label.text = "Status: extracting action items..."
        self.action_items_label.text = "Please wait..."
        self.extraction_future = self.executor.submit(
            self.meeting_service.extract_action_items,
            meeting_id,
        )
        self.extraction_future.add_done_callback(
            self._extraction_finished,
        )

    def _extraction_finished(self, future: Future[int]) -> None:
        if self.is_shutting_down:
            return

        Clock.schedule_once(
            lambda _dt: self._show_extraction_result(future),
        )

    def _show_extraction_result(self, future: Future[int]) -> None:
        if self.is_shutting_down:
            return

        try:
            count = future.result()
        except Exception as error:
            self.status_label.text = f"Status: extraction failed: {error}"
            self.action_items_label.text = "Could not load action items"
            return

        self.refresh_action_items(None, update_status=False)

        if count == 0:
            self.status_label.text = "Status: no action items found"
        else:
            self.status_label.text = f"Status: extracted {count} action item(s)"

    def refresh_action_items(
        self,
        _button: Button | None,
        update_status: bool = True,
    ) -> None:
        if self.current_meeting_id is None:
            self.action_items_label.text = (
                "Submit a meeting before refreshing action items"
            )
            return

        items = self.meeting_service.list_action_items(
            self.current_meeting_id,
        )

        if not items:
            self.action_items_label.text = "No action items"
            if update_status:
                self.status_label.text = "Status: action items refreshed"
            return

        self.action_items_label.text = "\n".join(
            self._format_action_item(item) for item in items
        )
        if update_status:
            self.status_label.text = "Status: action items refreshed"

    @staticmethod
    def _format_action_item(item: Any) -> str:
        owner = getattr(item, "owner", None)
        owner_text = f" — {owner}" if owner else ""
        return f"• [{item.status}] {item.description}{owner_text}"

    def shutdown(self) -> None:
        self.is_shutting_down = True

        if self.transcription_future is not None:
            self.transcription_future.cancel()
        if self.extraction_future is not None:
            self.extraction_future.cancel()
        if self.summary_future is not None:
            self.summary_future.cancel()

        self.executor.shutdown(wait=False, cancel_futures=True)

    def _update_meeting_summary_text_size(
        self,
        label: Label,
        width: float,
    ) -> None:
        label.text_size = (width, None)

    def generate_meeting_summary(self, _button: Button) -> None:
        if self.current_meeting_id is None:
            self.meeting_summary_label.text = (
                "Submit a meeting before generating a summary"
            )
            return

        if (
            self.transcription_future is not None
            and not self.transcription_future.done()
        ):
            self.status_label.text = "Status: transcription is still in progress"
            return

        if self.summary_future is not None and not self.summary_future.done():
            self.status_label.text = "Status: summary already in progress"
            return

        meeting_id = self.current_meeting_id
        self.status_label.text = "Status: generating meeting summary..."
        self.meeting_summary_label.text = "Generating summary..."

        self.summary_future = self.executor.submit(
            self.meeting_service.generate_meeting_summary,
            meeting_id,
        )
        self.summary_future.add_done_callback(
            self._summary_finished,
        )

    def _summary_finished(self, future: Future[str]) -> None:
        if self.is_shutting_down:
            return

        Clock.schedule_once(
            lambda _dt: self._show_meeting_summary_result(future),
        )

    def _show_meeting_summary_result(
        self,
        future: Future[str],
    ) -> None:
        if self.is_shutting_down:
            return

        try:
            summary = future.result()
        except Exception as error:
            self.status_label.text = f"Status: summary failed: {error}"
            self.meeting_summary_label.text = "Could not generate summary"
            return

        self.meeting_summary_label.text = summary
        self.status_label.text = "Status: meeting summary generated"


class KanbanScreen(Screen):
    def __init__(
        self,
        meeting_service: MeetingService,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        self.meeting_service = meeting_service
        self.current_meeting_id: int | None = None

        layout = BoxLayout(orientation="vertical", spacing=10, padding=20)

        self.title_label = Label(
            text="Kanban board",
            font_size="28sp",
            size_hint_y=None,
            height=50,
        )

        self.summary_label = Label(
            text="Open: 0 | Done: 0 | Verified: 0",
            size_hint_y=None,
            height=40,
        )

        self.deadlines_label = Label(
            text="Upcoming deadlines\nNo upcoming deadlines",
            halign="left",
            valign="top",
            size_hint_y=None,
            height=120,
        )
        self.deadlines_label.bind(
            width=self._update_deadlines_text_size,
        )

        board_scroll = ScrollView(do_scroll_y=False)

        columns = BoxLayout(
            orientation="horizontal",
            spacing=10,
            size_hint_x=None,
            width=1200,
        )

        board_scroll.add_widget(columns)

        self.open_column = self._create_column("Open")
        self.done_column = self._create_column("Done")
        self.verified_column = self._create_column("Verified")

        columns.add_widget(self.open_column)
        columns.add_widget(self.done_column)
        columns.add_widget(self.verified_column)

        refresh_button = Button(
            text="Refresh board",
            size_hint_y=None,
            height=50,
        )
        refresh_button.bind(on_press=self.refresh_board)

        back_button = Button(
            text="Back to meeting",
            size_hint_y=None,
            height=50,
        )
        back_button.bind(on_press=self.go_back_to_meeting)

        layout.add_widget(self.title_label)
        layout.add_widget(board_scroll)
        layout.add_widget(self.deadlines_label)
        layout.add_widget(refresh_button)
        layout.add_widget(back_button)
        self.add_widget(layout)

    def _create_column(self, title: str) -> BoxLayout:
        column = BoxLayout(
            orientation="vertical",
            spacing=10,
            padding=10,
        )

        column.add_widget(
            Label(
                text=title,
                font_size="22sp",
                size_hint_y=None,
                height=40,
            )
        )

        return column

    def _update_deadlines_text_size(
        self,
        label: Label,
        width: float,
    ) -> None:
        label.text_size = (width, None)

    def refresh_board(self, _button: Button) -> None:
        items = self.meeting_service.list_action_items(
            self.current_meeting_id,
        )

        self.open_column.clear_widgets()
        self.done_column.clear_widgets()
        self.verified_column.clear_widgets()

        self.open_column.add_widget(Label(text="Open", font_size="22sp"))
        self.done_column.add_widget(Label(text="Done", font_size="22sp"))
        self.verified_column.add_widget(Label(text="Verified", font_size="22sp"))

        for item in items:
            owner = item.owner or "All / unassigned"
            due_date = item.due_date or "No deadline"

            card = BoxLayout(
                orientation="vertical",
                spacing=5,
                size_hint_y=None,
                height=200,
            )

            item_label = Label(
                text=(f"• {item.description}\nOwner: {owner}\nDue: {due_date}"),
                halign="left",
                valign="top",
                size_hint_y=None,
                height=100,
            )
            item_label.bind(width=self._update_item_text_size)
            card.add_widget(item_label)

            actions = BoxLayout(
                orientation="horizontal",
                spacing=5,
                size_hint_y=None,
                height=45,
            )

            if item.status == "open":
                done_button = Button(text="Mark done")
                done_button.bind(
                    on_press=lambda _button, item_id=item.id: self._mark_done(item_id)
                )
                actions.add_widget(done_button)

            elif item.status == "done":
                verify_button = Button(text="Verify")
                verify_button.bind(
                    on_press=lambda _button, item_id=item.id: self._verify(item_id)
                )
                actions.add_widget(verify_button)

                reopen_button = Button(text="Reopen")
                reopen_button.bind(
                    on_press=lambda _button, item_id=item.id: self._reopen(item_id)
                )
                actions.add_widget(reopen_button)

            else:
                reopen_button = Button(text="Reopen")
                reopen_button.bind(
                    on_press=lambda _button, item_id=item.id: self._reopen(item_id)
                )
                actions.add_widget(reopen_button)

            delete_button = Button(text="Delete")
            delete_button.bind(
                on_press=lambda _button, item_id=item.id: self._delete(item_id)
            )
            actions.add_widget(delete_button)
            card.add_widget(actions)

            if item.status == "open":
                self.open_column.add_widget(card)
            elif item.status == "done":
                self.done_column.add_widget(card)
            else:
                self.verified_column.add_widget(card)

        open_count = sum(item.status == "open" for item in items)
        done_count = sum(item.status == "done" for item in items)
        verified_count = sum(item.status == "verified" for item in items)

        self.deadlines_label.text = "\n".join(
            f"• {item.due_date} — {item.description} — "
            f"{item.owner or 'All / unassigned'}"
            for item in sorted(
                (
                    item
                    for item in items
                    if item.status == "open" and item.due_date is not None
                ),
                key=lambda item: item.due_date,
            )
        )

        self.title_label.text = (
            "Kanban board\n"
            f"Open: {open_count} | Done: {done_count} | "
            f"Verified: {verified_count}"
        )

    def go_back_to_meeting(self, _button: Button) -> None:
        manager = self.parent

        if not isinstance(manager, ScreenManager):
            return

        manager.current = "meeting"

    def _update_item_text_size(
        self,
        label: Label,
        width: float,
    ) -> None:
        label.text_size = (width, None)

    def _mark_done(self, action_item_id: int) -> None:
        self.meeting_service.mark_action_item_done(action_item_id)
        self.refresh_board(None)

    def _verify(self, action_item_id: int) -> None:
        self.meeting_service.verify_action_item(action_item_id)
        self.refresh_board(None)

    def _reopen(self, action_item_id: int) -> None:
        self.meeting_service.reopen_action_item(action_item_id)
        self.refresh_board(None)

    def _delete(self, action_item_id: int) -> None:
        self.meeting_service.delete_action_item(action_item_id)
        self.refresh_board(None)


class MeetNoteApp(App):
    title = "MeetNote"

    def build(self) -> ScreenManager:
        manager = ScreenManager()
        meeting_service = self._create_meeting_service()

        meeting_screen = MeetingScreen(
            meeting_service=meeting_service,
            name="meeting",
        )
        kanban_screen = KanbanScreen(
            meeting_service=meeting_service,
            name="kanban",
        )

        manager.add_widget(meeting_screen)
        manager.add_widget(kanban_screen)

        return manager

    def _create_meeting_service(self) -> MeetingService:
        data_directory = Path("data")
        data_directory.mkdir(parents=True, exist_ok=True)

        transcriber_name = os.environ.get(
            "MEETNOTE_TRANSCRIBER",
            "fake",
        ).lower()

        if transcriber_name == "whisper":
            transcriber = LocalWhisperTranscriber(
                model_size="base",
                device="cpu",
                compute_type="int8",
            )
        else:
            transcriber = FakeTranscriber()

        action_extractor_name = os.environ.get(
            "MEETNOTE_ACTION_EXTRACTOR",
            "fake",
        ).lower()

        if action_extractor_name == "gemini":
            action_item_extractor = GeminiActionItemExtractor()
        else:
            action_item_extractor = FakeActionItemExtractor()

        return MeetingService(
            database_path=data_directory / "meetnote.db",
            action_item_extractor=action_item_extractor,
            transcriber=transcriber,
        )

    def on_stop(self) -> None:
        root = self.root

        if isinstance(root, ScreenManager):
            for screen in root.screens:
                if isinstance(screen, MeetingScreen):
                    screen.shutdown()
