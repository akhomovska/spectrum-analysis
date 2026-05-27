
import csv, random, sys, tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except:
    Figure = None
    FigureCanvasTkAgg = None


def install_packages():
    try:
        import numpy, matplotlib
        return True
    except:
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "matplotlib", "-q"])
            return True
        except:
            return False


def generate_signal(sample_rate, duration, num_signals, noise_level):
    import numpy as np
    time = np.linspace(0, duration, int(sample_rate * duration))
    signal = np.zeros(len(time))
    frequencies, amplitudes = [], []
    for i in range(num_signals):
        freq = random.uniform(5, sample_rate / 2 - 50)
        amp = random.uniform(0.1, 2.0)
        frequencies.append(freq)
        amplitudes.append(amp)
        signal += amp * np.sin(2 * np.pi * freq * time)
    signal += np.random.normal(0, noise_level, len(signal))
    return time, signal, frequencies, amplitudes


def compute_fft(signal, sample_rate):
    import numpy as np
    fft_result = np.fft.fft(signal)
    num_bins = len(signal) // 2
    fft_positive = fft_result[:num_bins]
    freq_bins = np.fft.fftfreq(len(signal), 1 / sample_rate)[:num_bins]
    power_spectrum = np.abs(fft_positive) ** 2
    return freq_bins, power_spectrum


def calculate_metrics(power_spectrum, amplitudes, freq_bins):
    import numpy as np
    total_power = np.sum(power_spectrum)
    signal_power = sum(a ** 2 / 2 for a in amplitudes)
    spectral_efficiency = signal_power / (total_power / len(power_spectrum))
    threshold = 0.1 * np.max(power_spectrum)
    occupied_bins = np.sum(power_spectrum > threshold)
    bandwidth = occupied_bins * (freq_bins[1] - freq_bins[0])
    return spectral_efficiency, bandwidth, occupied_bins


class SpectrumApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Аналіз ефективності частотного спектру")
        self.geometry("900x700")
        self.minsize(800, 650)
        self._configure_style()
        self._create_variables()
        self._create_widgets()
        self.last_results = None

    def _configure_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f5f7fb")
        style.configure("Header.TLabel", background="#f5f7fb", font=("Arial", 16, "bold"))
        style.configure("TLabel", background="#f5f7fb", font=("Arial", 10))
        style.configure("TButton", font=("Arial", 10), padding=6)
        style.configure("Result.TLabel", background="#ffffff", font=("Arial", 11), padding=10)

    def _create_variables(self):
        self.n_var = tk.StringVar(value="5")
        self.duration_var = tk.StringVar(value="10")
        self.sample_rate_var = tk.StringVar(value="1000")
        self.noise_var = tk.StringVar(value="0.05")

    def _create_widgets(self):
        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="Аналіз ефективності частотного спектру", style="Header.TLabel").pack(anchor="w")
        content = ttk.Frame(main)
        content.pack(fill="both", expand=True, pady=(14, 0))
        left = ttk.Frame(content)
        left.pack(side="left", fill="y", padx=(0, 16))
        right = ttk.Frame(content)
        right.pack(side="right", fill="both", expand=True)
        self._create_input_panel(left)
        self._create_result_panel(right)

    def _create_input_panel(self, parent):
        input_frame = ttk.LabelFrame(parent, text="Параметри", padding=12)
        input_frame.pack(fill="x")
        self._add_entry(input_frame, "Кількість частот (n)", self.n_var, 0)
        self._add_entry(input_frame, "Тривалість (сек)", self.duration_var, 2)
        self._add_entry(input_frame, "Частота дискретизації (Гц)", self.sample_rate_var, 4)
        self._add_entry(input_frame, "Рівень шуму", self.noise_var, 6)

        buttons = ttk.Frame(parent)
        buttons.pack(fill="x", pady=14)
        ttk.Button(buttons, text="Розрахувати", command=self.calculate).pack(fill="x", pady=3)
        ttk.Button(buttons, text="Показати таблицю", command=self.show_table).pack(fill="x", pady=3)
        ttk.Button(buttons, text="Показати графік", command=self.show_chart).pack(fill="x", pady=3)
        ttk.Button(buttons, text="Додати до таблиці", command=self.add_to_table).pack(fill="x", pady=3)
        ttk.Button(buttons, text="Очистити", command=self.clear_results).pack(fill="x", pady=3)

        export_frame = ttk.LabelFrame(parent, text="Експорт", padding=8)
        export_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(export_frame, text="Експорт в TXT", command=self.export_to_txt).pack(fill="x", pady=2)
        ttk.Button(export_frame, text="Експорт в CSV", command=self.export_to_csv).pack(fill="x", pady=2)

        import_frame = ttk.LabelFrame(parent, text="Імпорт", padding=8)
        import_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(import_frame, text="Імпорт з файлу", command=self.import_from_file).pack(fill="x", pady=2)

    def _add_entry(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(8, 2))
        entry = ttk.Entry(parent, textvariable=variable, width=26)
        entry.grid(row=row + 1, column=0, sticky="ew")
        parent.columnconfigure(0, weight=1)
        return entry

    def _create_result_panel(self, parent):
        result_frame = ttk.LabelFrame(parent, text="Результат", padding=12)
        result_frame.pack(fill="x")
        self.result_label = ttk.Label(result_frame, text="Введіть параметри та натисніть кнопку.",
                                      style="Result.TLabel", justify="left", anchor="nw")
        self.result_label.pack(fill="x")

        self.output_tabs = ttk.Notebook(parent)
        self.output_tabs.pack(fill="both", expand=True, pady=(14, 0))

        table_frame = ttk.Frame(self.output_tabs, padding=12)
        chart_frame = ttk.Frame(self.output_tabs, padding=12)
        self.output_tabs.add(table_frame, text="Таблиця")
        self.output_tabs.add(chart_frame, text="Графік")

        columns = ("num", "n", "duration", "sample_rate", "efficiency", "bandwidth", "papr")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)

        self.table.heading("#0", text="№")
        self.table.heading("n", text="n")
        self.table.heading("duration", text="Час (с)")
        self.table.heading("sample_rate", text="Fs (Гц)")
        self.table.heading("efficiency", text="Ефективність")
        self.table.heading("bandwidth", text="Ширина смуги")
        self.table.heading("papr", text="PAPR")

        self.table.column("#0", width=40, anchor="center")
        self.table.column("n", width=50, anchor="center")
        self.table.column("duration", width=70, anchor="center")
        self.table.column("sample_rate", width=70, anchor="center")
        self.table.column("efficiency", width=100, anchor="center")
        self.table.column("bandwidth", width=100, anchor="center")
        self.table.column("papr", width=80, anchor="center")

        self.table.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        scrollbar.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scrollbar.set)

        self._create_chart_panel(chart_frame)

    def _create_chart_panel(self, parent):
        if Figure is None:
            ttk.Label(parent, text="Встановіть matplotlib").pack(anchor="w")
            self.figure = self.chart_axes = self.chart_canvas = None
            return
        self.figure = Figure(figsize=(5.4, 3.4), dpi=100)
        self.chart_axes = self.figure.add_subplot(111)
        self.chart_canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)
        self._draw_empty_chart()

    def _draw_empty_chart(self):
        if not self.chart_axes: return
        self.chart_axes.clear()
        self.chart_axes.set_title("Ефективність спектру")
        self.chart_axes.set_xlabel("Кількість частот")
        self.chart_axes.set_ylabel("Ефективність")
        self.chart_axes.set_ylim(0, 1.05)
        self.chart_axes.grid(True, linestyle="--", alpha=0.35)
        self.figure.tight_layout()
        self.chart_canvas.draw()

    def _read_inputs(self):
        try:
            n = int(self.n_var.get())
            duration = float(self.duration_var.get())
            sample_rate = int(self.sample_rate_var.get())
            noise = float(self.noise_var.get())
        except ValueError:
            raise ValueError("Введіть коректні числа.")
        if not 1 <= n <= 10: raise ValueError("Кількість частот: 1-10")
        if not 1 <= duration <= 60: raise ValueError("Тривалість: 1-60")
        if not 100 <= sample_rate <= 10000: raise ValueError("Частота: 100-10000")
        if not 0.01 <= noise <= 1.0: raise ValueError("Шум: 0.01-1.0")
        return n, duration, sample_rate, noise

    def _show_error(self, error):
        messagebox.showerror("Помилка", str(error))

    def _set_result(self, text):
        self.result_label.configure(text=text)

    def _collect_data(self):
        return {"n": self.n_var.get(), "duration": self.duration_var.get(), "sample_rate": self.sample_rate_var.get(),
                "noise": self.noise_var.get()}

    def _clear_table(self):
        for row in self.table.get_children(): self.table.delete(row)

    def calculate(self):
        try:
            n, duration, sample_rate, noise = self._read_inputs()
        except ValueError as e:
            self._show_error(e); return
        import numpy as np
        time, signal, frequencies, amplitudes = generate_signal(sample_rate, duration, n, noise)
        freq_bins, power_spectrum = compute_fft(signal, sample_rate)
        spectral_efficiency, bandwidth, occupied_bins = calculate_metrics(power_spectrum, amplitudes, freq_bins)
        peak_power, avg_power = np.max(signal ** 2), np.mean(signal ** 2)
        papr = 10 * np.log10(peak_power / avg_power)
        self.last_results = {"n": n, "duration": duration, "sample_rate": sample_rate,
                             "efficiency": spectral_efficiency, "bandwidth": bandwidth, "occupied_bins": occupied_bins,
                             "papr": papr, "frequencies": frequencies, "freq_bins": freq_bins,
                             "power_spectrum": power_spectrum}
        lines = [f"Результати:", f"Кількість частот: {n}", f"Частоти: {', '.join(f'{f:.1f}' for f in frequencies)} Гц",
                 f"Ефективність: {spectral_efficiency:.4f}", f"Ширина смуги: {bandwidth:.2f} Гц",
                 f"Зайняті біни: {occupied_bins}", f"PAPR: {papr:.2f} дБ"]
        self._set_result("\n".join(lines))

    def add_to_table(self):
        if not self.last_results: self.calculate()
        if not self.last_results: return
        r = self.last_results
        num = len(self.table.get_children()) + 1
        self.table.insert("", "end", text=str(num),
                          values=(r["n"], r["duration"], r["sample_rate"], f"{r['efficiency']:.4f}",
                                  f"{r['bandwidth']:.2f}", f"{r['papr']:.2f}"))
        self._set_result(f"Додано до таблиці! (№{num})")

    def show_table(self):
        if not self.last_results: self.calculate()
        if not self.last_results: return
        self._set_result("Таблиця показана.")
        self.output_tabs.select(0)

    def show_chart(self):
        if not self.last_results: self.calculate()
        if not self.last_results or not self.figure: return
        import numpy as np
        self.chart_axes.clear()
        freq_bins, power_spectrum = self.last_results["freq_bins"], self.last_results["power_spectrum"]
        normalized = power_spectrum / np.max(power_spectrum)
        self.chart_axes.fill_between(freq_bins, normalized, alpha=0.4, color='blue')
        self.chart_axes.plot(freq_bins, normalized, 'b-', linewidth=1)
        self.chart_axes.axhline(y=0.1, color='r', linestyle='--', label='10% поріг')
        self.chart_axes.axhline(y=0.5, color='orange', linestyle='--', label='50% поріг')
        self.chart_axes.set_title("Ефективність частотного спектру")
        self.chart_axes.set_xlabel("Частота (Гц)")
        self.chart_axes.set_ylabel("Нормована потужність")
        self.chart_axes.set_xlim([0, 250])
        self.chart_axes.set_ylim([0, 1.1])
        self.chart_axes.legend()
        self.chart_axes.grid(True, linestyle="--", alpha=0.35)
        self.figure.tight_layout()
        self.chart_canvas.draw()
        self.output_tabs.select(1)
        self._set_result("Графік побудовано.")

    def import_from_file(self):
        path = filedialog.askopenfilename(title="Імпорт",
                                          filetypes=(("Текстові файли", "*.txt"), ("CSV", "*.csv"), ("Усі", "*.*")))
        if not path: return
        path = Path(path)
        try:
            if path.suffix.lower() == ".txt":
                data = {}
                with path.open("r", encoding="utf-8") as file:
                    for line in file:
                        if "=" in line:
                            k, v = line.strip().split("=", 1)
                            data[k] = v
                if "n" in data: self.n_var.set(data["n"])
                if "duration" in data: self.duration_var.set(data["duration"])
                if "sample_rate" in data: self.sample_rate_var.set(data["sample_rate"])
                if "noise" in data: self.noise_var.set(data["noise"])
            self._set_result(f"Імпортовано: {path.name}")
        except Exception as e:
            self._show_error(str(e))

    def export_to_txt(self):
        path = filedialog.asksaveasfilename(title="Експорт TXT", defaultextension=".txt", filetypes=(("TXT", "*.txt"),))
        if not path: return
        try:
            data = self._collect_data()
            with Path(path).open("w", encoding="utf-8") as file:
                for k, v in data.items(): file.write(f"{k}={v}\n")
            self._set_result(f"Експортовано: {Path(path).name}")
        except Exception as e:
            self._show_error(str(e))

    def export_to_csv(self):
        path = filedialog.asksaveasfilename(title="Експорт CSV", defaultextension=".csv", filetypes=(("CSV", "*.csv"),))
        if not path: return
        try:
            data = self._collect_data()
            with Path(path).open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["key", "value"])
                for k, v in data.items(): writer.writerow([k, v])
            self._set_result(f"Експортовано: {Path(path).name}")
        except Exception as e:
            self._show_error(str(e))

    def clear_results(self):
        self._set_result("Введіть параметри та натисніть кнопку.")
        self._clear_table()
        if self.figure: self._draw_empty_chart()


if __name__ == "__main__":
    if install_packages():
        app = SpectrumApp()
        app.mainloop()