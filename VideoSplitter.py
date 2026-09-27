import os
import sys
import subprocess
import threading
import re
import math
import tkinter as tk
from tkinter import filedialog, messagebox

# ---------------------------------------------------------
# 1. 의존성 라이브러리 및 환경 자동 검사 (설치, 업데이트, 에디터 연동)
# ---------------------------------------------------------
def ensure_vscode_config():
    """VS Code 에디터에서 실행 시 올바른 파이썬 환경을 자동 인식하도록 지원"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        vscode_dir = os.path.join(script_dir, ".vscode")
        settings_path = os.path.join(vscode_dir, "settings.json")
        if not os.path.exists(settings_path):
            os.makedirs(vscode_dir, exist_ok=True)
            import json
            site_packages = os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages")
            config = {
                "python.defaultInterpreterPath": sys.executable,
                "python.analysis.extraPaths": [site_packages] if os.path.exists(site_packages) else [],
                "python.analysis.diagnosticSeverityOverrides": {
                    "reportMissingImports": "none"
                }
            }
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def ensure_dependencies():
    """
    프로그램 구동에 필요한 라이브러리를 검사하여 미설치 시 자동 설치하고,
    실행할 때마다 최신 버전으로 자동 업데이트합니다.
    """
    required_packages = [
        "imageio-ffmpeg",
        "customtkinter",
        "darkdetect",
        "packaging"
    ]
    
    # 1. 미설치 패키지 확인 및 즉시 설치
    missing = []
    for pkg in required_packages:
        mod = pkg.replace("-", "_")
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        print(f"[*] 필수 라이브러리 자동 설치 중: {', '.join(missing)}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        except Exception as e:
            print(f"[!] 라이브러리 설치 실패: {e}")

    # 2. 실행할 때마다 최신 버전 업데이트 확인
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", *required_packages],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        # 오프라인 상태이거나 네트워크 지연 시 정상 구동 유지
        pass

ensure_vscode_config()
ensure_dependencies()

# pyrefly: ignore [missing-import]
# type: ignore
import customtkinter as ctk

# pyrefly: ignore [missing-import]
# type: ignore
import imageio_ffmpeg

# Apple Human Interface Guideline Color Palette
COLOR_BG = ("#F5F5F7", "#1A1A1E")
COLOR_CARD = ("#FFFFFF", "#26262B")
COLOR_CARD_BORDER = ("#E5E5EA", "#383840")
COLOR_TEXT_PRIMARY = ("#1D1D1F", "#F5F5F7")
COLOR_TEXT_SECONDARY = ("#86868B", "#98989D")
COLOR_ACCENT = ("#0071E3", "#0A84FF")
COLOR_ACCENT_HOVER = ("#0077ED", "#006EDC")
COLOR_SECONDARY_BTN = ("#EAEAEA", "#36363C")
COLOR_SECONDARY_BTN_HOVER = ("#DCDCE2", "#45454C")
COLOR_DANGER = ("#FF3B30", "#FF453A")
COLOR_DANGER_HOVER = ("#D70015", "#D70015")
COLOR_BADGE_BG = ("#EBF4FF", "#18283E")
COLOR_BADGE_TEXT = ("#0071E3", "#5AC8FA")


class VideoSplitterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 창 기본 설정
        self.title("동영상 분할기 (Video Splitter)")
        self.geometry("600x740")
        self.minsize(580, 700)
        self.configure(fg_color=COLOR_BG)

        # 시스템 테마 연동
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # 상태 변수
        self.file_path = ""
        self.output_dir = ""
        self.total_seconds = 0
        self.total_file_size = 0
        self.video_info_str = ""
        self.is_processing = False
        self.current_process = None

        self.setup_fonts()
        self.create_widgets()
        self.center_window()

    def setup_fonts(self):
        # macOS SF Pro / Windows Segoe UI 조화 폰트
        self.font_title = ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        self.font_subtitle = ctk.CTkFont(family="Segoe UI", size=11)
        self.font_section = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        self.font_body = ctk.CTkFont(family="Segoe UI", size=12)
        self.font_body_bold = ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        self.font_small = ctk.CTkFont(family="Segoe UI", size=11)
        self.font_btn = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        self.font_main_btn = ctk.CTkFont(family="Segoe UI", size=15, weight="bold")

    def center_window(self):
        self.update_idletasks()
        w = 600
        h = 750
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = max(30, (self.winfo_screenheight() // 2) - (h // 2) - 30)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def create_widgets(self):
        # 최상단 메인 패딩 컨테이너
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=22, pady=(16, 20))

        # -------------------------------------------------------------
        # 1. Apple 스타일 헤더 바 (신호등 도트 + 타이틀 + 테마 전환)
        # -------------------------------------------------------------
        header_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 14))

        # 왼쪽: macOS 신호등 도트 장식
        dots_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        dots_frame.pack(side="left", padx=(2, 10))

        for color in ["#FF5F56", "#FFBD2E", "#27C93F"]:
            dot = ctk.CTkFrame(dots_frame, width=12, height=12, corner_radius=6, fg_color=color)
            dot.pack(side="left", padx=3)

        # 타이틀 & 서브타이틀
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=4)

        lbl_title = ctk.CTkLabel(
            title_box, 
            text="동영상 분할기", 
            font=self.font_title, 
            text_color=COLOR_TEXT_PRIMARY
        )
        lbl_title.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            title_box, 
            text="화질 손상 없는 무손실 초고속 분할 • Lossless Stream Copy", 
            font=self.font_subtitle, 
            text_color=COLOR_TEXT_SECONDARY
        )
        lbl_sub.pack(anchor="w")

        # 오른쪽: 테마 전환 세그먼트 버튼 (System / Light / Dark)
        self.theme_segment = ctk.CTkSegmentedButton(
            header_frame,
            values=["💻 시스템", "☀️ 라이트", "🌙 다크"],
            font=self.font_small,
            command=self.change_theme,
            corner_radius=8,
            selected_color=COLOR_ACCENT[0],
            selected_hover_color=COLOR_ACCENT_HOVER[0]
        )
        self.theme_segment.set("💻 시스템")
        self.theme_segment.pack(side="right")

        # -------------------------------------------------------------
        # 2. 카드 1: 동영상 파일 선택
        # -------------------------------------------------------------
        card_file = self.create_card(main_container)
        card_file.pack(fill="x", pady=(0, 12))

        # 카드 헤더
        header_f = ctk.CTkFrame(card_file, fg_color="transparent")
        header_f.pack(fill="x", padx=16, pady=(14, 8))
        
        ctk.CTkLabel(
            header_f, 
            text="🎬  원본 동영상 선택", 
            font=self.font_section, 
            text_color=COLOR_TEXT_PRIMARY
        ).pack(side="left")

        self.btn_select_file = ctk.CTkButton(
            header_f,
            text="파일 선택...",
            width=90,
            height=30,
            corner_radius=8,
            font=self.font_btn,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self.select_file
        )
        self.btn_select_file.pack(side="right")

        # 파일 정보 표시 영역
        self.file_info_frame = ctk.CTkFrame(
            card_file, 
            fg_color=COLOR_BG, 
            corner_radius=10,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        self.file_info_frame.pack(fill="x", padx=16, pady=(0, 14))

        self.lbl_file_name = ctk.CTkLabel(
            self.file_info_frame,
            text="선택된 동영상 파일이 없습니다 (MP4, MOV, MKV 지원)",
            font=self.font_body,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w"
        )
        self.lbl_file_name.pack(fill="x", padx=14, pady=(10, 4))

        # 메타데이터 뱃지 영역 (용량, 재생시간 등)
        self.meta_frame = ctk.CTkFrame(self.file_info_frame, fg_color="transparent")
        self.meta_frame.pack(fill="x", padx=14, pady=(0, 8))

        self.lbl_meta_size = self.create_badge(self.meta_frame, "📦 용량: -")
        self.lbl_meta_size.pack(side="left", padx=(0, 6))

        self.lbl_meta_dur = self.create_badge(self.meta_frame, "⏱️ 재생시간: -")
        self.lbl_meta_dur.pack(side="left", padx=(0, 6))

        self.lbl_meta_res = self.create_badge(self.meta_frame, "🎞️ 해상도: -")
        self.lbl_meta_res.pack(side="left")

        # -------------------------------------------------------------
        # 3. 카드 2: 저장 폴더 선택
        # -------------------------------------------------------------
        card_dir = self.create_card(main_container)
        card_dir.pack(fill="x", pady=(0, 12))

        header_d = ctk.CTkFrame(card_dir, fg_color="transparent")
        header_d.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(
            header_d, 
            text="📂  저장 위치", 
            font=self.font_section, 
            text_color=COLOR_TEXT_PRIMARY
        ).pack(side="left")

        dir_btns = ctk.CTkFrame(header_d, fg_color="transparent")
        dir_btns.pack(side="right")

        self.btn_open_dir = ctk.CTkButton(
            dir_btns,
            text="폴더 열기",
            width=80,
            height=30,
            corner_radius=8,
            font=self.font_small,
            fg_color=COLOR_SECONDARY_BTN,
            hover_color=COLOR_SECONDARY_BTN_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            command=self.open_output_dir
        )
        self.btn_open_dir.pack(side="left", padx=(0, 6))

        self.btn_select_dir = ctk.CTkButton(
            dir_btns,
            text="변경...",
            width=70,
            height=30,
            corner_radius=8,
            font=self.font_small,
            fg_color=COLOR_SECONDARY_BTN,
            hover_color=COLOR_SECONDARY_BTN_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            command=self.select_directory
        )
        self.btn_select_dir.pack(side="left")

        self.dir_info_frame = ctk.CTkFrame(
            card_dir, 
            fg_color=COLOR_BG, 
            corner_radius=10,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        self.dir_info_frame.pack(fill="x", padx=16, pady=(0, 14))

        self.lbl_dir = ctk.CTkLabel(
            self.dir_info_frame,
            text="기본: 원본 동영상과 동일한 위치",
            font=self.font_small,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w"
        )
        self.lbl_dir.pack(fill="x", padx=14, pady=8)

        # -------------------------------------------------------------
        # 4. 카드 3: 분할 용량 설정 & 프리셋
        # -------------------------------------------------------------
        card_size = self.create_card(main_container)
        card_size.pack(fill="x", pady=(0, 12))

        header_s = ctk.CTkFrame(card_size, fg_color="transparent")
        header_s.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(
            header_s, 
            text="⚙️  분할 용량 설정", 
            font=self.font_section, 
            text_color=COLOR_TEXT_PRIMARY
        ).pack(side="left")

        # 프리셋 세그먼트 버튼 (Apple 세그먼트 컨트롤 스타일)
        self.preset_segment = ctk.CTkSegmentedButton(
            card_size,
            values=["200 MB", "500 MB", "1 GB", "2 GB", "직접 입력"],
            font=self.font_small,
            command=self.on_preset_selected,
            corner_radius=8,
            selected_color=COLOR_ACCENT[0],
            selected_hover_color=COLOR_ACCENT_HOVER[0]
        )
        self.preset_segment.set("500 MB")
        self.preset_segment.pack(fill="x", padx=16, pady=(0, 10))

        # 사용자 입력 및 단위 선택
        input_row = ctk.CTkFrame(card_size, fg_color="transparent")
        input_row.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            input_row, 
            text="조각당 목표 용량:", 
            font=self.font_body, 
            text_color=COLOR_TEXT_PRIMARY
        ).pack(side="left", padx=(0, 8))

        self.ent_size = ctk.CTkEntry(
            input_row,
            width=110,
            height=32,
            corner_radius=8,
            font=self.font_body_bold,
            border_color=COLOR_CARD_BORDER,
            justify="center"
        )
        self.ent_size.insert(0, "500")
        self.ent_size.pack(side="left", padx=(0, 8))
        self.ent_size.bind("<KeyRelease>", lambda e: self.update_estimation())

        self.unit_var = ctk.StringVar(value="MB")
        self.combo_unit = ctk.CTkOptionMenu(
            input_row,
            variable=self.unit_var,
            values=["MB", "GB"],
            width=80,
            height=32,
            corner_radius=8,
            font=self.font_body,
            fg_color=COLOR_SECONDARY_BTN,
            button_color=COLOR_SECONDARY_BTN_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            command=lambda val: self.update_estimation()
        )
        self.combo_unit.pack(side="left")

        # 예상 분할 결과 알림 바 (Apple 스타일 정보 팁)
        self.est_frame = ctk.CTkFrame(
            card_size, 
            fg_color=COLOR_BADGE_BG, 
            corner_radius=8
        )
        self.est_frame.pack(fill="x", padx=16, pady=(0, 14))

        self.lbl_estimation = ctk.CTkLabel(
            self.est_frame,
            text="💡 동영상을 선택하면 예상 분할 조각 수가 계산됩니다.",
            font=self.font_small,
            text_color=COLOR_BADGE_TEXT,
            anchor="w"
        )
        self.lbl_estimation.pack(fill="x", padx=12, pady=6)

        # -------------------------------------------------------------
        # 5. 카드 4: 진행 상황 & 상태 표시
        # -------------------------------------------------------------
        card_prog = self.create_card(main_container)
        card_prog.pack(fill="x", pady=(0, 14))

        prog_header = ctk.CTkFrame(card_prog, fg_color="transparent")
        prog_header.pack(fill="x", padx=16, pady=(14, 6))

        ctk.CTkLabel(
            prog_header, 
            text="📊  진행 상황", 
            font=self.font_section, 
            text_color=COLOR_TEXT_PRIMARY
        ).pack(side="left")

        self.lbl_pct = ctk.CTkLabel(
            prog_header, 
            text="0%", 
            font=self.font_body_bold, 
            text_color=COLOR_ACCENT
        )
        self.lbl_pct.pack(side="right")

        # Apple 스타일 라운드 프로그레스 바
        self.progress_bar = ctk.CTkProgressBar(
            card_prog,
            height=8,
            corner_radius=4,
            progress_color=COLOR_ACCENT,
            fg_color=COLOR_CARD_BORDER
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 8))

        # 하단 상태 문구 + 취소 버튼
        status_row = ctk.CTkFrame(card_prog, fg_color="transparent")
        status_row.pack(fill="x", padx=16, pady=(0, 12))

        self.lbl_status = ctk.CTkLabel(
            status_row,
            text="대기 중...",
            font=self.font_small,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w"
        )
        self.lbl_status.pack(side="left", fill="x", expand=True)

        self.btn_cancel = ctk.CTkButton(
            status_row,
            text="작업 취소",
            width=70,
            height=26,
            corner_radius=6,
            font=self.font_small,
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            command=self.cancel_processing
        )
        self.btn_cancel.pack(side="right")
        self.btn_cancel.pack_forget() # 진행 중일 때만 표시

        # -------------------------------------------------------------
        # 6. 하단 주 실행 버튼 (Apple 메인 액션 버튼)
        # -------------------------------------------------------------
        self.btn_start = ctk.CTkButton(
            main_container,
            text="▶  동영상 분할 시작",
            height=46,
            corner_radius=12,
            font=self.font_main_btn,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self.start_splitting_thread
        )
        self.btn_start.pack(fill="x", pady=(2, 0))

    def create_card(self, parent):
        return ctk.CTkFrame(
            parent,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            corner_radius=14
        )

    def create_badge(self, parent, text):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=self.font_small,
            fg_color=COLOR_SECONDARY_BTN,
            text_color=COLOR_TEXT_SECONDARY,
            corner_radius=6,
            padx=8,
            pady=2
        )

    def change_theme(self, mode):
        if mode == "☀️ 라이트":
            ctk.set_appearance_mode("Light")
        elif mode == "🌙 다크":
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("System")

    def on_preset_selected(self, preset):
        if preset == "200 MB":
            self.ent_size.delete(0, "end")
            self.ent_size.insert(0, "200")
            self.unit_var.set("MB")
        elif preset == "500 MB":
            self.ent_size.delete(0, "end")
            self.ent_size.insert(0, "500")
            self.unit_var.set("MB")
        elif preset == "1 GB":
            self.ent_size.delete(0, "end")
            self.ent_size.insert(0, "1")
            self.unit_var.set("GB")
        elif preset == "2 GB":
            self.ent_size.delete(0, "end")
            self.ent_size.insert(0, "2")
            self.unit_var.set("GB")
        self.update_estimation()

    def select_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("모든 지원 동영상 (*.mp4, *.mov, *.mkv ...)", "*.mp4 *.mov *.mkv *.m4v *.avi *.webm"),
                ("MP4 동영상 (*.mp4)", "*.mp4"),
                ("Apple QuickTime MOV (*.mov)", "*.mov"),
                ("Matroska MKV (*.mkv)", "*.mkv"),
                ("모든 파일 (*.*)", "*.*")
            ]
        )
        if not file_path:
            return

        self.file_path = file_path
        file_name = os.path.basename(file_path)
        
        # 파일명 줄임 처리 (너무 길면 잘림 방지)
        display_name = file_name if len(file_name) < 48 else file_name[:44] + "..."
        self.lbl_file_name.configure(text=display_name, font=self.font_body_bold, text_color=COLOR_TEXT_PRIMARY)

        # 기본 저장 폴더 설정
        if not self.output_dir:
            self.output_dir = os.path.dirname(file_path)
            self.update_dir_label(self.output_dir)

        # 백그라운드에서 동영상 정보(길이, 크기, 해상도) 분석
        threading.Thread(target=self.probe_file_info, daemon=True).start()

    def probe_file_info(self):
        try:
            self.total_file_size = os.path.getsize(self.file_path)
            size_mb = self.total_file_size / (1024 * 1024)
            size_str = f"{size_mb / 1024:.2f} GB" if size_mb >= 1024 else f"{size_mb:.1f} MB"
            self.lbl_meta_size.configure(text=f"📦 {size_str}")

            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            probe_cmd = [ffmpeg_exe, "-i", self.file_path]
            result = subprocess.run(
                probe_cmd, 
                stderr=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                text=True, 
                encoding="utf-8", 
                errors="ignore"
            )
            output = result.stderr

            # 재생 시간 파싱
            dur_match = re.search(r"Duration: (\d{2}):(\d{2}):([\d.]+)", output)
            if dur_match:
                h, m, s = map(float, dur_match.groups())
                self.total_seconds = h * 3600 + m * 60 + s
                dur_str = f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
                self.lbl_meta_dur.configure(text=f"⏱️ {dur_str}")

            # 해상도 파싱
            res_match = re.search(r"Video:.*?(\d{3,4}x\d{3,4})", output)
            if res_match:
                self.lbl_meta_res.configure(text=f"🎞️ {res_match.group(1)}")
            else:
                self.lbl_meta_res.configure(text="🎞️ 영상 감지됨")

            # 예상 분할 조각 수 즉시 계산
            self.update_estimation()

        except Exception as e:
            print(f"정보 파싱 오류: {e}")

    def select_directory(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.output_dir = dir_path
            self.update_dir_label(dir_path)

    def update_dir_label(self, path):
        display_path = path if len(path) < 55 else "..." + path[-50:]
        self.lbl_dir.configure(text=display_path, text_color=COLOR_TEXT_PRIMARY)

    def open_output_dir(self):
        target = self.output_dir or (os.path.dirname(self.file_path) if self.file_path else "")
        if target and os.path.exists(target):
            os.startfile(target)
        else:
            messagebox.showinfo("안내", "저장 폴더가 아직 설정되지 않았거나 존재하지 않습니다.")

    def update_estimation(self):
        if not self.file_path or self.total_file_size == 0:
            self.lbl_estimation.configure(text="💡 동영상을 선택하면 예상 분할 결과가 계산됩니다.")
            return

        try:
            size_val = float(self.ent_size.get())
            if size_val <= 0:
                raise ValueError
        except ValueError:
            self.lbl_estimation.configure(text="⚠️ 올바른 숫자의 분할 용량을 입력해주세요.")
            return

        unit = self.unit_var.get()
        chunk_bytes = size_val * (1024 * 1024 * 1024 if unit == "GB" else 1024 * 1024)

        if chunk_bytes >= self.total_file_size:
            self.lbl_estimation.configure(
                text="⚠️ 목표 분할 용량이 원본 크기보다 크거나 같습니다 (분할 불필요)."
            )
            return

        est_parts = math.ceil(self.total_file_size / chunk_bytes)
        self.lbl_estimation.configure(
            text=f"💡 예상 분할 결과: 약 {est_parts}개 파일로 분할 (각 ~{size_val:g} {unit}, 무손실)"
        )

    def start_splitting_thread(self):
        if self.is_processing:
            return

        if not self.file_path or not os.path.exists(self.file_path):
            messagebox.showerror("오류", "분할할 동영상 파일을 먼저 선택해주세요.")
            return

        try:
            size_val = float(self.ent_size.get())
            if size_val <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("오류", "올바른 숫자의 분할 용량을 입력해주세요.")
            return

        unit = self.unit_var.get()
        chunk_size_bytes = size_val * (1024 * 1024 * 1024 if unit == "GB" else 1024 * 1024)

        if not self.output_dir:
            self.output_dir = os.path.dirname(self.file_path)

        self.is_processing = True
        self.btn_start.configure(state="disabled", text="⏳  분할 작업 진행 중...")
        self.btn_cancel.pack(side="right")
        self.progress_bar.set(0)
        self.lbl_pct.configure(text="0%")

        threading.Thread(target=self.split_video, args=(chunk_size_bytes,), daemon=True).start()

    def cancel_processing(self):
        if self.current_process and self.is_processing:
            try:
                self.current_process.terminate()
            except Exception:
                pass
            self.update_ui(0, "작업이 사용자에 의해 중단되었습니다.")
            self.reset_ui()
            messagebox.showwarning("취소됨", "동영상 분할 작업이 중단되었습니다.")

    def split_video(self, chunk_size_bytes):
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

            # 1. 파일 크기 및 재생 시간 검증
            self.update_ui(0, "동영상 스트림 분석 중...")
            total_file_size = os.path.getsize(self.file_path)

            if self.total_seconds == 0:
                probe_cmd = [ffmpeg_exe, "-i", self.file_path]
                res = subprocess.run(
                    probe_cmd, 
                    stderr=subprocess.PIPE, 
                    stdout=subprocess.PIPE, 
                    text=True, 
                    encoding="utf-8", 
                    errors="ignore"
                )
                dur_match = re.search(r"Duration: (\d{2}):(\d{2}):([\d.]+)", res.stderr)
                if not dur_match:
                    raise Exception("동영상의 재생 시간을 확인할 수 없습니다.")
                h, m, s = map(float, dur_match.groups())
                self.total_seconds = h * 3600 + m * 60 + s

            if total_file_size <= chunk_size_bytes:
                messagebox.showwarning("안내", "설정한 분할 용량이 원본 파일 크기보다 크거나 같습니다.")
                self.reset_ui()
                return

            # 비트레이트 기반 세그먼트 시간(초) 산출
            avg_bitrate = total_file_size / self.total_seconds
            segment_duration = chunk_size_bytes / avg_bitrate

            file_ext = os.path.splitext(self.file_path)[1].lower() or ".mp4"
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]
            output_pattern = os.path.join(self.output_dir, f"{base_name}_part_%03d{file_ext}")

            # 2. 화질 손상 없는 스트림 복사(-c copy) 모드로 세그먼트 분할
            # -map 0: 모든 비디오, 오디오(다국어 등), 자막 스트림을 온전히 보존
            cmd = [
                ffmpeg_exe, "-y", "-i", self.file_path,
                "-c", "copy",
                "-map", "0",
                "-f", "segment",
                "-segment_time", str(segment_duration),
                "-reset_timestamps", "1"
            ]

            # MP4 및 MOV 파일은 빠른 웹/플레이어 재생을 위해 moov atom 전진 배치(+faststart)
            if file_ext in [".mp4", ".mov", ".m4v"]:
                cmd.extend(["-movflags", "+faststart"])

            cmd.append(output_pattern)

            self.current_process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )

            # 3. 실시간 진행률 추적
            while True:
                line = self.current_process.stderr.readline()
                if not line and self.current_process.poll() is not None:
                    break

                time_match = re.search(r"time=(\d{2}):(\d{2}):([\d.]+)", line)
                if time_match:
                    th, tm, ts = map(float, time_match.groups())
                    curr_sec = th * 3600 + tm * 60 + ts
                    pct = min(int((curr_sec / self.total_seconds) * 100), 100)
                    msg = f"분할 진행 중... {curr_sec:.0f}초 / {self.total_seconds:.0f}초 처리 완료"
                    self.update_ui(pct, msg)

            if self.current_process.returncode == 0:
                self.update_ui(100, "분할 작업 완료! 🎉")
                # 완료 팝업 (폴더 열기 옵션 제공)
                if messagebox.askyesno(
                    "분할 완료", 
                    f"동영상 분할이 성공적으로 완료되었습니다!\n\n저장 경로:\n{self.output_dir}\n\n결과 폴더를 여시겠습니까?"
                ):
                    self.open_output_dir()
            elif not self.is_processing:
                # 사용자가 취소한 경우
                pass
            else:
                raise Exception("FFmpeg 스트림 복사 처리 중 오류가 발생했습니다.")

        except Exception as e:
            if self.is_processing:
                messagebox.showerror("오류 발생", f"작업 중 오류가 발생했습니다:\n{str(e)}")
        finally:
            self.reset_ui()

    def update_ui(self, pct, status_text):
        self.after(0, lambda: self.progress_bar.set(pct / 100.0))
        self.after(0, lambda: self.lbl_pct.configure(text=f"{pct}%"))
        self.after(0, lambda: self.lbl_status.configure(text=status_text))

    def reset_ui(self):
        self.is_processing = False
        self.current_process = None
        self.after(0, lambda: self.btn_start.configure(state="normal", text="▶  동영상 분할 시작"))
        self.after(0, lambda: self.btn_cancel.pack_forget())


if __name__ == "__main__":
    app = VideoSplitterApp()
    app.mainloop()
