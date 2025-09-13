# game.py (complete fixed version)
import pygame
import sys
import serial
import time
import os
import random
import statistics
import subprocess
from collections import deque
from pyvidplayer2 import Video
from settings import *
from sprites import Ball, Hole, Barrier, Button, Particle
from fpdf import FPDF
import matplotlib.pyplot as plt

# Helper function
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_state = "user_type_selection"

        # User Profile Data
        self.user_name, self.user_gender, self.user_age, self.user_type = "", "", "", ""
        
        # Gameplay Session Data
        self.level_sequence = ["Easy", "Medium", "Hard"]
        self.current_level_index = 0
        self.completed_levels_metrics = []
        self.current_level_metrics = {}

        # Hardware Data
        self.current_fsr = 0
        self.accel_data = [0, 0, 0]
        self.gyro_data = [0, 0, 0]
        self.fsr_threshold = FSR_THRESHOLD
        
        # Settings
        self.music_enabled = True
        self.hud_font = pygame.font.Font(None, HUD_FONT_SIZE)
        
        self.menu_background = None
        try:
            bg_image = pygame.image.load("assets/MenuBackground.jpg").convert()
            self.menu_background = pygame.transform.scale(bg_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except Exception as e:
            print(f"Warning: Could not load menu background image. {e}")

        try:
            self.ser = serial.Serial(SERIAL_PORT, 115200, timeout=0.02)
            print(f"Successfully connected to NeuroGrip Ball on {SERIAL_PORT}")
            self.ser.flushInput()
        except serial.SerialException:
            print(f"Error: Could not connect to NeuroGrip Ball on {SERIAL_PORT}.")
            print("[INFO] Running in Keyboard Simulation Mode.")
            self.ser = None

    def _read_hardware_data(self):
        if not self.ser: return False
        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8').strip()
                data = line.split(',')
                if len(data) == 7:
                    self.current_fsr = int(data[0])
                    self.accel_data = [int(data[1]), int(data[2]), int(data[3])]
                    self.gyro_data = [int(data[4]), int(data[5]), int(data[6])]
                    return True
        except Exception as e:
            print(f"Error reading hardware data: {e}")
        return False

    def run(self):
        while self.running:
            if self.game_state == "user_type_selection": self._get_user_type()
            elif self.game_state == "user_info_entry": self._get_user_info()
            elif self.game_state == "main_menu": self._show_main_menu()
            elif self.game_state == "settings": self._show_settings_menu()
            elif self.game_state == "playing":
                level_name = self.level_sequence[self.current_level_index]
                self._play_level(level_name)
            elif self.game_state == "ask_continue": self._ask_to_continue()
            elif self.game_state == "generate_report":
                self._generate_report()
                self.current_level_index, self.completed_levels_metrics = 0, []
                self.game_state = "main_menu"

        if self.ser: self.ser.close()
        pygame.quit()
        sys.exit()

    def _handle_menu_events(self, buttons):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "quit"
            for button in buttons:
                if button.is_clicked(event): return button.text
            if event.type == pygame.MOUSEBUTTONDOWN:
                for button in buttons:
                    if button.is_hovered: button.is_pressed = True
            if event.type == pygame.MOUSEBUTTONUP:
                for button in buttons: button.is_pressed = False
        return None

    def _draw_menu_background(self, title):
        if self.menu_background: self.screen.blit(self.menu_background, (0, 0))
        else: self.screen.fill(BLUE)
        if title.strip():
            title_text = pygame.font.Font(None, 74).render(title, True, WHITE)
            self.screen.blit(title_text, title_text.get_rect(center=(SCREEN_WIDTH / 2, 100)))

    def _get_user_type(self):
        pygame.display.set_caption("Select User Type")
        button_font = pygame.font.Font(None, 50)
        buttons = [
            Button(SCREEN_WIDTH/2 - 200, 250, 400, 80, "Normal User (Testing)", button_font, WHITE, GREEN),
            Button(SCREEN_WIDTH/2 - 200, 350, 400, 80, "Rehabilitation Patient", button_font, WHITE, BLUE)
        ]
        
        type_running = True
        while type_running:
            self.clock.tick(60)
            mouse_pos = pygame.mouse.get_pos()
            for button in buttons: button.check_hover(mouse_pos)
            action = self._handle_menu_events(buttons)
            if action == "quit": type_running = False; self.running = False
            elif action == "Normal User (Testing)": 
                self.user_type = "normal"
                self.game_state, type_running = "user_info_entry", False
            elif action == "Rehabilitation Patient": 
                self.user_type = "rehab"
                self.game_state, type_running = "user_info_entry", False
            
            self._draw_menu_background("Select User Type")
            for button in buttons: button.draw(self.screen)
            pygame.display.flip()

    def _get_user_info(self):
        pygame.display.set_caption("Enter User Information")
        input_font = pygame.font.Font(None, 40)
        input_boxes = {"name": pygame.Rect(SCREEN_WIDTH/2 - 150, 200, 300, 50), "gender": pygame.Rect(SCREEN_WIDTH/2 - 150, 300, 300, 50), "age": pygame.Rect(SCREEN_WIDTH/2 - 150, 400, 300, 50)}
        active_box, user_inputs = None, {"name": "", "gender": "", "age": ""}
        start_button = Button(SCREEN_WIDTH/2 - 100, 550, 200, 60, "Start Game", input_font, WHITE, GREEN)
        
        input_running = True
        while input_running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: input_running = False; self.running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    active_box = next((key for key, box in input_boxes.items() if box.collidepoint(event.pos)), None)
                if event.type == pygame.KEYDOWN and active_box:
                    if event.key == pygame.K_RETURN: active_box = None
                    elif event.key == pygame.K_BACKSPACE: user_inputs[active_box] = user_inputs[active_box][:-1]
                    else: user_inputs[active_box] += event.unicode
                if start_button.is_clicked(event):
                    self.user_name, self.user_gender, self.user_age = user_inputs["name"], user_inputs["gender"], user_inputs["age"]
                    if all(user_inputs.values()): self.game_state, input_running = "main_menu", False
                    else: print("Please fill in all user information.")
            
            mouse_pos = pygame.mouse.get_pos()
            start_button.check_hover(mouse_pos)
            self._draw_menu_background("   ")
            for key, box in input_boxes.items():
                self.screen.blit(input_font.render(key.capitalize() + ":", True, WHITE), (box.x, box.y - 30))
                pygame.draw.rect(self.screen, YELLOW if active_box == key else WHITE, box, 2)
                self.screen.blit(input_font.render(user_inputs[key], True, WHITE), (box.x + 5, box.y + 5))
            start_button.draw(self.screen)
            pygame.display.flip()

    def _show_main_menu(self):
        pygame.display.set_caption("Main Menu")
        button_font = pygame.font.Font(None, 50)
        buttons = [Button(SCREEN_WIDTH/2 - 150, 250, 300, 80, "Start Game", button_font, WHITE, GREEN), 
                   Button(SCREEN_WIDTH/2 - 150, 350, 300, 80, "Settings", button_font, WHITE, YELLOW), 
                   Button(SCREEN_WIDTH/2 - 150, 450, 300, 80, "Quit", button_font, WHITE, RED)]
        
        menu_running = True
        while menu_running:
            self.clock.tick(60)
            mouse_pos = pygame.mouse.get_pos()
            for button in buttons: button.check_hover(mouse_pos)
            action = self._handle_menu_events(buttons)
            if action == "quit": menu_running = False; self.running = False
            elif action == "Start Game": self.current_level_index, self.completed_levels_metrics, self.game_state, menu_running = 0, [], "playing", False
            elif action == "Settings": self.game_state, menu_running = "settings", False
            elif action == "Quit": menu_running = False; self.running = False
            self._draw_menu_background("   ")
            for button in buttons: button.draw(self.screen)
            pygame.display.flip()

    def _show_settings_menu(self):
        pygame.display.set_caption("Settings")
        button_font = pygame.font.Font(None, 50)
        music_button = Button(SCREEN_WIDTH/2 - 150, 250, 300, 80, "", button_font, WHITE, YELLOW)
        back_button = Button(SCREEN_WIDTH/2 - 150, 350, 300, 80, "Back", button_font, WHITE, GREEN)
        buttons = [music_button, back_button]
        settings_running = True
        while settings_running:
            self.clock.tick(60)
            music_button.text = f"Music: {'ON' if self.music_enabled else 'OFF'}"
            mouse_pos = pygame.mouse.get_pos()
            for button in buttons: button.check_hover(mouse_pos)
            action = self._handle_menu_events(buttons)
            if action == "quit": settings_running = False; self.running = False
            elif action == music_button.text: self.music_enabled = not self.music_enabled
            elif action == "Back": self.game_state, settings_running = "main_menu", False
            self._draw_menu_background("Settings")
            for button in buttons: button.draw(self.screen)
            pygame.display.flip()

    def _ask_to_continue(self):
        pygame.display.set_caption("Level Complete!")
        button_font = pygame.font.Font(None, 50)
        buttons = [Button(SCREEN_WIDTH/2 - 220, 400, 200, 80, "Continue", button_font, WHITE, GREEN), 
                   Button(SCREEN_WIDTH/2 + 20, 400, 200, 80, "End & Report", button_font, WHITE, BLUE)]
        ask_running = True
        while ask_running:
            self.clock.tick(60)
            mouse_pos = pygame.mouse.get_pos()
            for button in buttons: button.check_hover(mouse_pos)
            action = self._handle_menu_events(buttons)
            if action == "quit": ask_running = False; self.running = False
            elif action == "Continue": self.game_state, ask_running = "playing", False
            elif action == "End & Report": self.game_state, ask_running = "generate_report", False
            self._draw_menu_background(" ") 
            title_font = pygame.font.Font(None, 74)
            continue_text_surf = title_font.render(f"Continue to {self.level_sequence[self.current_level_index]}?", True, WHITE)
            continue_text_rect = continue_text_surf.get_rect(center=(SCREEN_WIDTH / 2, 250))
            self.screen.blit(continue_text_surf, continue_text_rect)
            for button in buttons: button.draw(self.screen)
            pygame.display.flip()
            
    def _play_level(self, level_name):
        pygame.display.set_caption(f"Maze Game - {level_name}")
        try:
            game_video = Video("assets/BackgroundVid.mp4") if os.path.exists("assets/BackgroundVid.mp4") else None
            if self.music_enabled and os.path.exists("assets/GameMusic.mp3"): pygame.mixer.music.load("assets/GameMusic.mp3"); pygame.mixer.music.play(-1)
        except Exception as e: game_video = None; print(f"Warning: Video/music not loaded. {e}")
        
        level_map = LEVELS[level_name]
        barriers, all_sprites, particles = pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group()
        player_start_pos, hole = None, None
        
        for r, row in enumerate(level_map):
            for c, tile in enumerate(row):
                x, y = c * TILE_SIZE, r * TILE_SIZE
                if tile == 'W': barriers.add(Barrier(x, y, TILE_SIZE, TILE_SIZE))
                elif tile == 'P': player_start_pos = (x + TILE_SIZE//2, y + TILE_SIZE//2)
                elif tile == 'H': hole = Hole(x + TILE_SIZE//2, y + TILE_SIZE//2)
        
        all_sprites.add(barriers)
        if player_start_pos is None: print(f"Error: No player start found in level {level_name}"); self.game_state = "main_menu"; return
        if hole is None: print(f"Error: No hole found in level {level_name}"); self.game_state = "main_menu"; return
        all_sprites.add(hole)
        
        player = Ball(player_start_pos[0], player_start_pos[1])
        player_velocity = pygame.math.Vector2(0, 0)
        target_velocity = pygame.math.Vector2(0, 0)
        
        start_vec, hole_vec = pygame.math.Vector2(player_start_pos), pygame.math.Vector2(hole.rect.center)
        shortest_path = start_vec.distance_to(hole_vec) * 1.5

        self.current_level_metrics = {"LevelName": level_name, "Duration": 0, "Max_FSR": 0, "Min_FSR_Move": MAX_FSR_VALUE, "FSR_Readings_Move": [], "Grip_Lapses": 0, "Collision_Count": 0, "Path_Points": [player.rect.center], "Shortest_Path_Length": shortest_path}
        start_time, level_running = time.time(), True
        
        while level_running:
            dt = self.clock.tick(60) / 1000.0
            dt = min(dt, 0.1)
            hardware_connected = self._read_hardware_data()
            
            if hardware_connected:
                tilt_x = clamp(self.accel_data[0] / TILT_SENSITIVITY, -1, 1)
                tilt_y = clamp(self.accel_data[1] / TILT_SENSITIVITY, -1, 1)
                if self.current_fsr > self.fsr_threshold: target_velocity.x = tilt_x * PLAYER_SPEED; target_velocity.y = tilt_y * PLAYER_SPEED
                else: target_velocity.x = 0; target_velocity.y = 0
                if target_velocity.length() > 0:
                    self.current_level_metrics["FSR_Readings_Move"].append(self.current_fsr)
                    self.current_level_metrics["Max_FSR"] = max(self.current_level_metrics["Max_FSR"], self.current_fsr)
                    self.current_level_metrics["Min_FSR_Move"] = min(self.current_level_metrics["Min_FSR_Move"], self.current_fsr)
            else:
                keys = pygame.key.get_pressed()
                target_velocity.x = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * PLAYER_SPEED
                target_velocity.y = (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * PLAYER_SPEED
                if target_velocity.length() > 0:
                    sim_fsr = random.uniform(FSR_THRESHOLD + 200, MAX_FSR_VALUE - 500)
                    self.current_fsr = sim_fsr
                    self.current_level_metrics["FSR_Readings_Move"].append(sim_fsr)
                    self.current_level_metrics["Max_FSR"] = max(self.current_level_metrics["Max_FSR"], sim_fsr)
                    self.current_level_metrics["Min_FSR_Move"] = min(self.current_level_metrics["Min_FSR_Move"], sim_fsr)
                else: self.current_fsr = 0

            player_velocity = player_velocity.lerp(target_velocity, PLAYER_ACCELERATION)
            for event in pygame.event.get():
                if event.type == pygame.QUIT: level_running = False; self.running = False

            old_x, old_y = player.rect.x, player.rect.y
            
            player.rect.x += player_velocity.x * dt
            x_collisions = pygame.sprite.spritecollide(player, barriers, False)
            if x_collisions: player.rect.x = old_x; player_velocity.x *= -PLAYER_BOUNCINESS; self.current_level_metrics["Collision_Count"] += 1
            
            player.rect.y += player_velocity.y * dt
            y_collisions = pygame.sprite.spritecollide(player, barriers, False)
            if y_collisions: player.rect.y = old_y; player_velocity.y *= -PLAYER_BOUNCINESS; self.current_level_metrics["Collision_Count"] += 1
            
            self.current_level_metrics["Path_Points"].append(player.rect.center)
            
            if pygame.math.Vector2(player.rect.center).distance_to(hole.rect.center) < 15:
                self.current_level_metrics["Duration"] = time.time() - start_time
                self.completed_levels_metrics.append(self.current_level_metrics.copy())
                self.current_level_index += 1
                if self.current_level_index >= len(self.level_sequence): self.game_state = "generate_report"
                else: self.game_state = "ask_continue"
                level_running = False
            
            if player_velocity.length() > 20 and random.random() < 0.5:
                particles.add(Particle(player.rect.centerx, player.rect.centery, YELLOW, random.randint(2, 5), (-player_velocity.x * 0.1, -player_velocity.y * 0.1)))
            if x_collisions or y_collisions:
                for _ in range(10): particles.add(Particle(player.rect.centerx, player.rect.centery, RED, random.randint(3, 7), (random.uniform(-3, 3), random.uniform(-3, 3))))

            particles.update()
            if game_video: game_video.draw(self.screen, (0, 0), force_draw=False)
            else: self.screen.fill(BLACK)
            
            all_sprites.draw(self.screen)
            particles.draw(self.screen)
            player.draw_with_shadow(self.screen)
            self._draw_hud(start_time)
            pygame.display.flip()

        pygame.mixer.music.stop()
        if game_video: game_video.close()

    def _draw_hud(self, start_time):
        elapsed_time = time.time() - start_time
        mins, secs = int(elapsed_time // 60), int(elapsed_time % 60)
        timer_text = f"{mins:02}:{secs:02}"
        self.screen.blit(self.hud_font.render(timer_text, True, WHITE), TIMER_POS)
        
        self.screen.blit(self.hud_font.render("Grip:", True, WHITE), (GRIP_METER_POS[0] - 70, GRIP_METER_POS[1] - 4))
        pygame.draw.rect(self.screen, GRIP_METER_BG_COLOR, pygame.Rect(GRIP_METER_POS, GRIP_METER_SIZE))
        fill_ratio = clamp(self.current_fsr / MAX_FSR_VALUE, 0, 1)
        pygame.draw.rect(self.screen, GRIP_METER_FILL_COLOR, pygame.Rect(GRIP_METER_POS[0], GRIP_METER_POS[1], GRIP_METER_SIZE[0] * fill_ratio, GRIP_METER_SIZE[1]))
        threshold_x = GRIP_METER_POS[0] + (FSR_THRESHOLD / MAX_FSR_VALUE) * GRIP_METER_SIZE[0]
        pygame.draw.line(self.screen, GRIP_METER_THRESHOLD_COLOR, (threshold_x, GRIP_METER_POS[1]), (threshold_x, GRIP_METER_POS[1] + GRIP_METER_SIZE[1]), 2)
        
        status_text = "Hardware: Connected" if self.ser else "Hardware: Simulated"
        status_color = GREEN if self.ser else YELLOW
        self.screen.blit(self.hud_font.render(status_text, True, status_color), (SCREEN_WIDTH - 250, 10))
        
        if self.ser:
            bar_width, bar_height = 100, 10; center_x = SCREEN_WIDTH // 2
            x_tilt = clamp(self.accel_data[0] / 8000, -1, 1)
            pygame.draw.rect(self.screen, (100, 100, 100), (center_x - bar_width//2, 40, bar_width, bar_height))
            pygame.draw.rect(self.screen, RED, (center_x, 40, x_tilt * bar_width//2, bar_height))
            y_tilt = clamp(self.accel_data[1] / 8000, -1, 1)
            pygame.draw.rect(self.screen, (100, 100, 100), (center_x - bar_width//2, 60, bar_width, bar_height))
            pygame.draw.rect(self.screen, BLUE, (center_x, 60, y_tilt * bar_width//2, bar_height))

    def _create_performance_chart(self):
        """Generates a bar chart of performance metrics and saves it as an image."""
        if not self.completed_levels_metrics:
            return None

        labels = [m['LevelName'] for m in self.completed_levels_metrics]
        collisions = [m['Collision_Count'] for m in self.completed_levels_metrics]
        
        # Calculate CoV for each level to display on the chart
        level_covs = []
        for metrics in self.completed_levels_metrics:
            if len(metrics['FSR_Readings_Move']) > 1:
                mean_fsr = statistics.mean(metrics['FSR_Readings_Move'])
                stdev_fsr = statistics.stdev(metrics['FSR_Readings_Move'])
                level_covs.append((stdev_fsr / mean_fsr) * 100 if mean_fsr > 0 else 0)
            else:
                level_covs.append(0)

        x = range(len(labels))
        width = 0.35
        
        fig, ax1 = plt.subplots(figsize=(8, 5))
        
        # Bar chart for collisions
        ax1.bar(x, collisions, width, label='Collisions', color='skyblue')
        ax1.set_ylabel('Total Collisions', color='skyblue')
        ax1.set_xlabel('Levels')
        ax1.tick_params(axis='y', labelcolor='skyblue')
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels)
        
        # Line chart for Grip CoV on a second y-axis
        ax2 = ax1.twinx()
        ax2.plot(x, level_covs, label='Grip CoV (%)', color='red', marker='o')
        ax2.set_ylabel('Grip CoV (%)', color='red')
        ax2.tick_params(axis='y', labelcolor='red')

        fig.suptitle('Performance Summary: Collisions and Grip Stability')
        fig.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        chart_filename = "performance_chart.png"
        plt.savefig(chart_filename)
        plt.close()
        return chart_filename

    def _generate_report(self):
        if not self.completed_levels_metrics: 
            print("No levels completed."); 
            return
        
        num_levels = len(self.completed_levels_metrics)
        
        # --- Process Data for Each Level ---
        level_specific_data = []
        for metrics in self.completed_levels_metrics:
            # Calculate CoV
            cov = 0
            if len(metrics['FSR_Readings_Move']) > 1:
                mean_fsr = statistics.mean(metrics['FSR_Readings_Move'])
                stdev_fsr = statistics.stdev(metrics['FSR_Readings_Move'])
                cov = (stdev_fsr / mean_fsr) * 100 if mean_fsr > 0 else 0
            
            # Calculate Path Efficiency
            path_len = sum(pygame.math.Vector2(p1).distance_to(p2) for p1, p2 in zip(metrics["Path_Points"][:-1], metrics["Path_Points"][1:]))
            shortest_path = metrics["Shortest_Path_Length"]
            path_eff = (shortest_path / path_len) * 100 if path_len > 0 else 0

            level_specific_data.append({
                "name": metrics['LevelName'],
                "duration": metrics['Duration'],
                "collisions": metrics['Collision_Count'],
                "cov": cov,
                "path_eff": path_eff
            })

        # --- Calculate Overall Averages ---
        avg_cov = statistics.mean([d['cov'] for d in level_specific_data])
        avg_collisions = statistics.mean([d['collisions'] for d in level_specific_data])
        avg_path_eff = statistics.mean([d['path_eff'] for d in level_specific_data])
        
        # --- Load or Generate Thresholds for Normal Users ---
        thresholds_file = "normal_user_thresholds.txt"
        if self.user_type == "normal":
            # Save this user's data as part of the threshold calculation
            self._update_normal_thresholds(thresholds_file, avg_cov, avg_collisions, avg_path_eff)
        
        # --- PDF Generation ---
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, txt="NeuroGrip Maze Game Report", ln=True, align="C")
        pdf.ln(10)

        # User and Session Info
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 8, txt=f"Player Name: {self.user_name}", ln=True)
        pdf.cell(0, 8, txt=f"Gender: {self.user_gender}", ln=True)
        pdf.cell(0, 8, txt=f"Age: {self.user_age}", ln=True)
        pdf.cell(0, 8, txt=f"User Type: {'Normal User' if self.user_type == 'normal' else 'Rehabilitation Patient'}", ln=True)
        pdf.cell(0, 8, txt=f"Session Date: {time.strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
        pdf.ln(5)
        
        # --- Level-by-Level Breakdown Table ---
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, txt="Level-by-Level Performance", ln=True)
        pdf.set_font("Arial", 'B', 10)
        # Table Header
        pdf.cell(40, 8, 'Level', 1, 0, 'C')
        pdf.cell(40, 8, 'Duration (s)', 1, 0, 'C')
        pdf.cell(35, 8, 'Collisions', 1, 0, 'C')
        pdf.cell(35, 8, 'Grip CoV (%)', 1, 0, 'C')
        pdf.cell(40, 8, 'Path Efficiency (%)', 1, 1, 'C')
        # Table Rows
        pdf.set_font("Arial", size=10)
        for data in level_specific_data:
            pdf.cell(40, 8, data['name'], 1, 0, 'C')
            pdf.cell(40, 8, f"{data['duration']:.2f}", 1, 0, 'C')
            pdf.cell(35, 8, str(data['collisions']), 1, 0, 'C')
            pdf.cell(35, 8, f"{data['cov']:.2f}", 1, 0, 'C')
            pdf.cell(40, 8, f"{data['path_eff']:.2f}", 1, 1, 'C')
        pdf.ln(10)

        # --- Overall Averages ---
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, txt="Overall Averages", ln=True)
        pdf.set_font("Arial", 'B', 10)
        # Table Header
        pdf.cell(40, 8, 'Metric', 1, 0, 'C')
        pdf.cell(40, 8, 'Average Value', 1, 1, 'C')
        
        # Table Rows
        pdf.set_font("Arial", size=10)
        pdf.cell(40, 8, 'Collisions', 1, 0, 'C')
        pdf.cell(40, 8, f"{avg_collisions:.2f}", 1, 1, 'C')
        
        pdf.cell(40, 8, 'Grip CoV (%)', 1, 0, 'C')
        pdf.cell(40, 8, f"{avg_cov:.2f}", 1, 1, 'C')
        
        pdf.cell(40, 8, 'Path Efficiency (%)', 1, 0, 'C')
        pdf.cell(40, 8, f"{avg_path_eff:.2f}", 1, 1, 'C')
        
        pdf.ln(10)

        # --- Comparison with Normal Thresholds for Rehab Patients ---
        if self.user_type == "rehab":
            thresholds = self._load_normal_thresholds(thresholds_file)
            if thresholds:
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, txt="Comparison with Normal User Benchmarks", ln=True)
                pdf.set_font("Arial", 'B', 10)
                
                # Table Header
                pdf.cell(40, 8, 'Metric', 1, 0, 'C')
                pdf.cell(40, 8, 'Your Score', 1, 0, 'C')
                pdf.cell(40, 8, 'Normal Avg', 1, 0, 'C')
                pdf.cell(40, 8, 'Difference', 1, 1, 'C')
                
                # Table Rows
                pdf.set_font("Arial", size=10)
                
                # Collisions comparison
                pdf.cell(40, 8, 'Collisions', 1, 0, 'C')
                pdf.cell(40, 8, f"{avg_collisions:.2f}", 1, 0, 'C')
                pdf.cell(40, 8, f"{thresholds['avg_collisions']:.2f}", 1, 0, 'C')
                diff = avg_collisions - thresholds['avg_collisions']
                pdf.cell(40, 8, f"{diff:+.2f}", 1, 1, 'C')
                
                # CoV comparison
                pdf.cell(40, 8, 'Grip CoV (%)', 1, 0, 'C')
                pdf.cell(40, 8, f"{avg_cov:.2f}", 1, 0, 'C')
                pdf.cell(40, 8, f"{thresholds['avg_cov']:.2f}", 1, 0, 'C')
                diff = avg_cov - thresholds['avg_cov']
                pdf.cell(40, 8, f"{diff:+.2f}", 1, 1, 'C')
                
                # Path Efficiency comparison
                pdf.cell(40, 8, 'Path Eff (%)', 1, 0, 'C')
                pdf.cell(40, 8, f"{avg_path_eff:.2f}", 1, 0, 'C')
                pdf.cell(40, 8, f"{thresholds['avg_path_eff']:.2f}", 1, 0, 'C')
                diff = avg_path_eff - thresholds['avg_path_eff']
                pdf.cell(40, 8, f"{diff:+.2f}", 1, 1, 'C')
                
                pdf.ln(10)

        # --- Visualizations ---
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, txt="Visual Performance Summary", ln=True)
        chart_filename = self._create_performance_chart()
        if chart_filename:
            pdf.image(chart_filename, x=15, y=None, w=180)
            os.remove(chart_filename)
        
        # --- Qualitative Summary ---
        pdf.add_page() # Put summary on a new page for clarity
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, txt="Performance Summary", ln=True)
        pdf.set_font("Arial", size=12)
        
        # Generate qualitative summary
        summary = self._generate_qualitative_summary(level_specific_data, avg_cov, avg_collisions, avg_path_eff)
        pdf.multi_cell(0, 8, txt=summary)
        
        # Save the PDF
        report_filename = f"NeuroGrip_Report_{self.user_name}_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf.output(report_filename)
        print(f"Report generated: {report_filename}")
        
        # Open the report
        try:
            if sys.platform == "win32": os.startfile(report_filename)
            elif sys.platform == "darwin": subprocess.call(["open", report_filename])
            else: subprocess.call(["xdg-open", report_filename])
        except: pass

    def _update_normal_thresholds(self, filename, avg_cov, avg_collisions, avg_path_eff):
        """Update the normal user thresholds with data from this session"""
        thresholds = {
            'avg_cov': [],
            'avg_collisions': [],
            'avg_path_eff': []
        }
        
        # Load existing data if available
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    for line in f:
                        key, values = line.strip().split(':')
                        if key in thresholds:
                            thresholds[key] = [float(v) for v in values.split(',')]
            except Exception as e:
                print(f"Error reading thresholds file: {e}")
        
        # Add new data
        thresholds['avg_cov'].append(avg_cov)
        thresholds['avg_collisions'].append(avg_collisions)
        thresholds['avg_path_eff'].append(avg_path_eff)
        
        # Calculate new averages
        result = {}
        for key, values in thresholds.items():
            result[key] = statistics.mean(values) if values else 0
        
        # Save updated data
        try:
            with open(filename, 'w') as f:
                for key, values in thresholds.items():
                    f.write(f"{key}:{','.join(map(str, values))}\n")
        except Exception as e:
            print(f"Error saving thresholds: {e}")
            
        return result

    def _load_normal_thresholds(self, filename):
        """Load normal user thresholds for comparison"""
        if not os.path.exists(filename):
            print(f"No thresholds file found: {filename}")
            return None
            
        try:
            thresholds = {}
            with open(filename, 'r') as f:
                for line in f:
                    key, values = line.strip().split(':')
                    values = [float(v) for v in values.split(',')]
                    thresholds[key] = statistics.mean(values) if values else 0
            return thresholds
        except Exception as e:
            print(f"Error loading thresholds: {e}")
            return None

    def _generate_qualitative_summary(self, level_data, avg_cov, avg_collisions, avg_path_eff):
        """Generate a qualitative summary of the player's performance"""
        summary = ""
        
        # Grip stability assessment
        if avg_cov < 15:
            summary += "Your grip control was exceptionally steady and consistent, indicating excellent force modulation skills. "
        elif avg_cov < 25:
            summary += "Your grip control was generally stable with some minor fluctuations. "
        else:
            summary += "Your grip control showed significant fluctuation, suggesting an opportunity to improve steadiness. "
        
        # Navigation accuracy assessment
        if avg_collisions < 5:
            summary += "Your navigational accuracy was very high with minimal collisions. "
        elif avg_collisions < 15:
            summary += "Your navigation was effective with a moderate number of collisions. "
        else:
            summary += "A high number of collisions suggests a focus on improving fine motor precision could be beneficial. "
        
        # Path efficiency assessment
        if avg_path_eff > 80:
            summary += "You followed an efficient path to the goal, demonstrating good spatial awareness. "
        elif avg_path_eff > 60:
            summary += "Your path to the goal was reasonably efficient with some room for improvement. "
        else:
            summary += "Your path to the goal was less efficient, suggesting opportunities to improve route planning. "
        
        # Level progression assessment
        if len(level_data) > 1:
            improvement = ""
            if level_data[-1]['cov'] < level_data[0]['cov']:
                improvement += "grip stability, "
            if level_data[-1]['collisions'] < level_data[0]['collisions']:
                improvement += "navigation accuracy, "
            if level_data[-1]['path_eff'] > level_data[0]['path_eff']:
                improvement += "path efficiency, "
            
            if improvement:
                summary += f"You showed improvement in {improvement.rstrip(', ')} as you progressed through the levels."
            else:
                summary += "Your performance remained consistent across all levels."
        
        return summary

if __name__ == "__main__":
    game = Game()
    game.run()