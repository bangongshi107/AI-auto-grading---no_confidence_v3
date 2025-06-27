import sys
import os
import datetime
import pathlib
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from ui_components.main_window import MainWindow
from api_service import ApiService
from config_manager import ConfigManager
from auto_thread import AutoThread
import winsound
import csv
import traceback

class SimpleNotificationDialog(QDialog):
    def __init__(self, title, message, sound_type='info', parent=None):
        super().__init__(parent)
        self.sound_type = sound_type
        self.setup_ui(title, message)
        self.setup_sound_timer()

    def setup_ui(self, title, message):
        self.setWindowTitle(title)
        self.setFixedSize(350, 150)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout()

        # 消息标签
        msg_label = QLabel(message)
        msg_label.setFont(QFont("Arial", 11))
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("padding: 20px;")
        layout.addWidget(msg_label)

        # 确定按钮
        button_layout = QHBoxLayout()
        close_btn = QPushButton("确定")
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)  # 支持回车键确认
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def setup_sound_timer(self):
        # 立即播放一次
        self.play_system_sound()

        # 设置2分钟重复定时器
        self.sound_timer = QTimer()
        self.sound_timer.timeout.connect(self.play_system_sound)
        self.sound_timer.start(120000)  # 60秒 = 1分钟

    def play_system_sound(self):
        """播放系统默认提示音，跟随用户系统设置"""
        try:
            if self.sound_type == 'error':
                # 系统错误声音
                winsound.MessageBeep(winsound.MB_ICONERROR)
            else:
                # 系统信息声音
                winsound.MessageBeep(winsound.MB_ICONINFORMATION)
        except Exception:
            # 如果系统声音不可用，使用默认beep
            try:
                winsound.Beep(800, 300)  # 备用方案
            except Exception:
                pass  # 完全静默失败

    def closeEvent(self, event):
        """窗口关闭时停止定时器"""
        if hasattr(self, 'sound_timer'):
            self.sound_timer.stop()
        super().closeEvent(event)

    def accept(self):
        """点击确定时停止定时器"""
        if hasattr(self, 'sound_timer'):
            self.sound_timer.stop()
        super().accept()


class SignalConnectionManager:
    def __init__(self):
        self.connections = []

    def connect(self, signal, slot, connection_type=Qt.AutoConnection):
        """安全地连接信号，避免重复"""
        # 先尝试断开可能存在的连接
        try:
            signal.disconnect(slot)
        except (TypeError, RuntimeError):
            pass

        # 建立新连接
        connection = signal.connect(slot, type=connection_type)
        self.connections.append((signal, slot))
        return connection

    def disconnect_all(self):
        """断开所有管理的连接"""
        for signal, slot in self.connections:
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        self.connections.clear()

class Application:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.config_manager = ConfigManager()
        self.api_service = ApiService(self.config_manager)
        self.worker = AutoThread(self.api_service)
        self.main_window = MainWindow(self.config_manager, self.api_service, self.worker)
        self.signal_manager = SignalConnectionManager()

        self._setup_application()

    def _setup_global_exception_hook(self):
        """设置全局异常钩子"""
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return

            error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            
            # 尝试记录到UI
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'log_message'):
                self.main_window.log_message(f"全局异常捕获:\n{error_msg}", is_error=True)
            
            # 尝试记录到文件
            try:
                # 确定日志目录的绝对路径
                if getattr(sys, 'frozen', False):
                    # 打包后，相对于exe文件
                    base_dir = pathlib.Path(sys.executable).parent
                else:
                    # 开发时，相对于main.py
                    base_dir = pathlib.Path(__file__).parent

                log_dir = base_dir / "logs"
                log_dir.mkdir(exist_ok=True)
                log_file = log_dir / f"global_error_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(error_msg)
            except Exception as e:
                print(f"写入全局异常日志失败: {e}")

            # 显示一个简单的错误对话框
            dialog = SimpleNotificationDialog(
                title="严重错误",
                message=f"发生了一个意外的严重错误，应用程序可能需要关闭。\n\n错误: {exc_value}",
                sound_type='error'
            )
            dialog.exec_()

        sys.excepthook = handle_exception

    def _setup_application(self):
        """初始化应用程序设置"""
        try:
            self._setup_global_exception_hook()
            self.connect_worker_signals()
            self.load_config()
            self._create_record_directory()
        except Exception as e:
            print(f"应用程序初始化失败: {str(e)}")
            sys.exit(1)

    def _create_record_directory(self):
        """创建记录目录"""
        try:
            if getattr(sys, 'frozen', False):
                # 如果是打包后的exe，使用exe所在的实际目录
                base_dir = pathlib.Path(sys.executable).parent
            else:
                # 否则，使用当前文件所在的目录
                base_dir = pathlib.Path(__file__).parent
            record_dir = base_dir / "阅卷记录"
            record_dir.mkdir(exist_ok=True)
        except OSError as e:
            self.main_window.log_message(f"创建记录目录失败: {str(e)}", is_error=True)

    def connect_worker_signals(self):
        """连接工作线程信号"""
        try:
            self.signal_manager.disconnect_all() # 断开旧连接

            self.signal_manager.connect(
                self.worker.update_signal,
                self.main_window.update_suggestion_text
            )
            self.signal_manager.connect(
                self.worker.log_signal,
                self.main_window.log_message
            )
            # self.signal_manager.connect(
            #     self.worker.progress_signal,
            #     self.main_window.update_progress
            # )
            self.signal_manager.connect(
                self.worker.record_signal,
                self.save_grading_record
            )

            # 任务正常完成
            self.signal_manager.connect(
                self.worker.finished_signal,
                self.show_completion_notification # 这个方法内部会调用 main_window.on_worker_finished
            )

            # 任务因错误中断
            if hasattr(self.worker, 'error_signal'): # 确保 AutoThread 有 error_signal
                self.signal_manager.connect(
                    self.worker.error_signal,
                    self.show_error_notification # 这个方法内部需要调用 main_window.on_worker_error
                )

            # 双评分差超过阈值中断
            if hasattr(self.worker, 'threshold_exceeded_signal'):
                self.signal_manager.connect(
                    self.worker.threshold_exceeded_signal,
                    self.show_threshold_exceeded_notification # 这个方法内部需要调用 main_window.on_worker_error
                )

        except Exception as e:
            # 避免在 main_window 可能还未完全初始化时调用其 log_message
            print(f"[CRITICAL_ERROR] 连接工作线程信号时出错: {str(e)}")
            if hasattr(self.main_window, 'log_message'):
                 self.main_window.log_message(f"连接工作线程信号时出错: {str(e)}", is_error=True)

    def show_completion_notification(self):
        """显示任务完成通知"""
        # 先调用原有的完成处理
        self.main_window.on_worker_finished()

        # 显示简洁的完成通知
        dialog = SimpleNotificationDialog(
            title="批次完成",
            message="✅ 本次自动阅卷已完成！\n\n请复查AI阅卷结果，人工审核0分、满分",
            sound_type='info',
            parent=self.main_window
        )
        dialog.exec_()

    def show_error_notification(self, error_message):
        """显示错误通知并恢复主窗口状态"""
        if hasattr(self.main_window, 'on_worker_error'):
            self.main_window.on_worker_error(error_message)
        else:
            print(f"[ERROR] MainWindow missing on_worker_error. Error: {error_message}")
            # 基本的后备恢复
            if self.main_window.isMinimized(): self.main_window.showNormal(); self.main_window.activateWindow()
            if hasattr(self.main_window, 'update_ui_state'): self.main_window.update_ui_state(is_running=False)

        dialog = SimpleNotificationDialog(
            title="阅卷中断",
            message=f"⚠️ 自动阅卷因发生错误而停止！\n\n错误: {error_message}\n请检查界面下方日志。",
            sound_type='error',
            parent=self.main_window
        )
        dialog.exec_()

    def show_threshold_exceeded_notification(self, reason):
        """显示双评分差超过阈值的通知并恢复主窗口状态"""
        specific_error_message = f"双评分差过大 ({reason})"
        if hasattr(self.main_window, 'on_worker_error'):
            self.main_window.on_worker_error(specific_error_message)
        else:
            print(f"[ERROR] MainWindow missing on_worker_error. Reason: {specific_error_message}")
            # 基本的后备恢复
            if self.main_window.isMinimized(): self.main_window.showNormal(); self.main_window.activateWindow()
            if hasattr(self.main_window, 'update_ui_state'): self.main_window.update_ui_state(is_running=False)

        dialog = SimpleNotificationDialog(
            title="双评分差过大",
            message=f"⚠️ {specific_error_message}，自动阅卷已中断！\n\n请检查日志并手动处理。",
            sound_type='error',
            parent=self.main_window
        )
        dialog.exec_()

    def load_config(self):
        """加载配置并设置到主窗口"""
        # 加载配置到内存
        self.config_manager.load_config()
        # 将配置加载到UI
        self.main_window.load_config_to_ui()

        # 更新API服务的配置
        self.api_service.update_config_from_manager()

        self.main_window.log_message("配置已成功加载并应用。")

    def _save_summary_record(self, record_data):
        """保存汇总记录到对应的CSV文件

        Args:
            record_data: 汇总记录数据
        """
        try:
            import csv
            import os

            # 获取当前日期
            date_str = record_data.get('timestamp', datetime.datetime.now().strftime('%Y%m%d_%H%M%S')).split('_')[0]

            # 创建记录目录
            if getattr(sys, 'frozen', False):
                # 如果是打包后的exe，使用exe所在的实际目录
                base_dir = pathlib.Path(sys.executable).parent
            else:
                # 否则，使用当前文件所在的目录
                base_dir = pathlib.Path(__file__).parent
            record_dir = base_dir / "阅卷记录"
            record_dir.mkdir(exist_ok=True)

            # 创建日期子目录
            date_dir = record_dir / date_str
            date_dir.mkdir(exist_ok=True)

            # 判断当前是否为双评模式
            dual_evaluation = self.worker.parameters.get('dual_evaluation', False)
            question_count = len(self.worker.parameters.get('question_configs', []))
            if question_count == 0:
                question_count = 1

            # 构建文件名
            formatted_date = datetime.datetime.strptime(date_str, '%Y%m%d').strftime('%Y年%m月%d日')
            csv_filename = f"{formatted_date}_共{question_count}题_{'双评' if dual_evaluation else '单评'}.csv"
            csv_filepath = date_dir / csv_filename

            # 从 record_data 构建汇总行，而不是依赖 summary_text
            status_map = {
                "completed": "正常完成",
                "error": "因错误中断",
                "threshold_exceeded": "因双评分差过大中断"
            }
            status_text = status_map.get(record_data.get('completion_status', 'unknown'), "未知状态")
            
            interrupt_reason = record_data.get('interrupt_reason')
            if interrupt_reason:
                status_text += f" ({interrupt_reason})"

            summary_fields = [
                f"--- 批次阅卷汇总 ({record_data.get('timestamp', 'N/A_N/A').split('_')[1]}) ---",
                f"状态: {status_text}",
                f"计划/完成: {record_data.get('total_questions_attempted', 'N/A')} / {record_data.get('questions_completed', 'N/A')} 个",
                f"总用时: {record_data.get('total_elapsed_time_seconds', 0):.2f} 秒",
                f"模式: {'双评' if record_data.get('dual_evaluation_enabled') else '单评'}",
            ]
            
            if record_data.get('dual_evaluation_enabled'):
                summary_fields.append(f"模型: {record_data.get('first_model_id', 'N/A')} vs {record_data.get('second_model_id', 'N/A')}")
            else:
                summary_fields.append(f"模型: {record_data.get('first_model_id', 'N/A')}")

            # 追加汇总行到文件并在前后添加空白行
            with open(csv_filepath, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 汇总行前添加2行空白行
                writer.writerow([])
                writer.writerow([])
                # 写入汇总行
                writer.writerow(summary_fields)
                # 汇总行后添加4行空白行，以区分不同批次阅卷记录
                writer.writerow([])
                writer.writerow([])
                writer.writerow([])
                writer.writerow([])

            self.main_window.log_message(f"已保存汇总记录到: {csv_filename}")
            return csv_filepath

        except Exception as e:
            self.main_window.log_message(f"保存汇总记录失败: {str(e)}", is_error=True)
            return None

    def save_grading_record(self, record_data):
        """
        重构后的保存阅卷记录到CSV文件的方法。
        - 动态构建CSV表头和行数据，支持单评和双评模式。
        - 包含置信度分数和理由，并对低置信度项进行标记。
        """
        try:
            # 记录汇总信息
            if record_data.get('record_type') == 'summary':
                return self._save_summary_record(record_data)

            # --- 1. 准备文件路径 ---
            date_str = record_data.get('timestamp', datetime.datetime.now().strftime('%Y%m%d_%H%M%S')).split('_')[0]
            
            if getattr(sys, 'frozen', False):
                base_dir = pathlib.Path(sys.executable).parent
            else:
                base_dir = pathlib.Path(__file__).parent
            
            record_dir = base_dir / "阅卷记录"
            record_dir.mkdir(exist_ok=True)
            date_dir = record_dir / date_str
            date_dir.mkdir(exist_ok=True)

            is_dual_run = record_data.get('is_dual_evaluation_run', False)
            question_count = record_data.get('total_questions_in_run', 1)
            if question_count == 0: question_count = 1

            formatted_date = datetime.datetime.strptime(date_str, '%Y%m%d').strftime('%Y年%m月%d日')
            csv_filename = f"{formatted_date}_共{question_count}题_{'双评' if is_dual_run else '单评'}.csv"
            csv_filepath = date_dir / csv_filename
            file_exists = os.path.isfile(csv_filepath)

            # --- 2. 格式化函数 ---
            def format_confidence(score_value):
                if score_value in [1, "1"]: return "!! 1"
                if score_value in [2, "2"]: return "!! 2"
                return str(score_value) if score_value is not None else "N/A"

            # --- 3. 动态构建表头和行 ---
            is_dual = record_data.get('is_dual_evaluation', False)
            timestamp_str = record_data.get('timestamp', '').split('_')[1] if '_' in record_data.get('timestamp', '') else record_data.get('timestamp', '')
            question_index_str = f"题目{record_data.get('question_index', 0)}"
            final_total_score_str = str(record_data.get('total_score', 0))

            headers = ["时间", "题目编号"]
            base_row = [timestamp_str, question_index_str]
            rows_to_write = []

            if is_dual:
                headers.extend(["API标识", "分差阈值", "学生答案摘要", "评分依据", "AI分项得分", "AI原始总分", "识别置信度", "置信度理由", "双评分差", "最终得分"])
                
                row1 = base_row + [
                    "API-1",
                    str(record_data.get('score_diff_threshold', "N/A")),
                    record_data.get('api1_student_answer_summary', 'N/A'),
                    record_data.get('api1_scoring_basis', 'N/A'),
                    str(record_data.get('api1_itemized_scores', [])),
                    str(record_data.get('api1_raw_score', 0.0)),
                    format_confidence(record_data.get('api1_confidence_score')),
                    record_data.get('api1_confidence_reason', 'N/A'),
                    f"{record_data.get('score_difference', 0.0):.2f}",
                    final_total_score_str
                ]
                row2 = base_row + [
                    "API-2",
                    str(record_data.get('score_diff_threshold', "N/A")),
                    record_data.get('api2_student_answer_summary', 'N/A'),
                    record_data.get('api2_scoring_basis', 'N/A'),
                    str(record_data.get('api2_itemized_scores', [])),
                    str(record_data.get('api2_raw_score', 0.0)),
                    format_confidence(record_data.get('api2_confidence_score')),
                    record_data.get('api2_confidence_reason', 'N/A'),
                    f"{record_data.get('score_difference', 0.0):.2f}",
                    final_total_score_str
                ]
                rows_to_write.extend([row1, row2])
            else: # 单评模式
                headers.extend(["学生答案摘要", "评分依据", "AI分项得分", "识别置信度", "置信度理由", "最终得分"])
                
                single_row = base_row + [
                    record_data.get('student_answer', '无法提取'),
                    record_data.get('reasoning_basis', '无法提取'),
                    record_data.get('sub_scores', 'N/A'),
                    format_confidence(record_data.get('confidence_score')),
                    record_data.get('confidence_reason', 'N/A'),
                    final_total_score_str
                ]
                rows_to_write.append(single_row)

            # --- 4. 写入文件 ---
            with open(csv_filepath, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(headers)
                writer.writerows(rows_to_write)

            self.main_window.log_message(f"已保存阅卷记录到: {csv_filename}")
            return csv_filepath

        except Exception as e:
            error_detail_full = traceback.format_exc()
            self.main_window.log_message(f"保存阅卷记录失败: {str(e)}\n详细错误:\n{error_detail_full}", is_error=True)
            return None

    def start_auto_evaluation(self):
        """开始自动阅卷"""
        try:
            # 检查必要设置
            if not self.main_window.check_required_settings():
                return

            self.worker.start()
        except Exception as e:
            self.main_window.log_message(f"运行自动阅卷失败: {str(e)}", is_error=True)

    def run(self):
        """运行应用程序"""
        # 显示主窗口
        self.main_window.show()

        # 运行应用程序事件循环
        result = self.app.exec_()
        return result

if __name__ == "__main__":
    # 创建应用程序实例
    app = Application()

    # 运行应用程序
    sys.exit(app.run())
