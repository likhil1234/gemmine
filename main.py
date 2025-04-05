import pygame
import sys
import random
import os
import json
import asyncio
from typing import Tuple, List, Set, Dict
from collections import deque
from datetime import datetime

# Initialize Pygame
pygame.init()

# Constants
class Colors:
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (220, 220, 220)
    DARK_GRAY = (40, 40, 40)
    BLUE = (70, 130, 180)
    GREEN = (34, 139, 34)
    RED = (178, 34, 34)
    YELLOW = (255, 215, 0)
    LIGHT_GRAY = (200, 200, 200)

# Configuration
GRID_SIZE = 800
WINDOW_WIDTH, WINDOW_HEIGHT = 1000, 800
SIDEBAR_WIDTH = 200
MENU_WIDTH, MENU_HEIGHT = 600, 600
FPS = 30
FONT = pygame.font.SysFont("Segoe UI", 28)
LEADERBOARD_FILE = "leaderboard.txt"
STATS_FILE = "game_stats.json"
GRID_OPTIONS = [4, 5, 6, 7, 8]

class GameAssets:
    def __init__(self):
        try:
            self.gem = pygame.transform.scale(pygame.image.load("gem.png"), (40, 40))
            self.mine = pygame.transform.scale(pygame.image.load("mine.png"), (40, 40))
            self.click_sound = pygame.mixer.Sound("click.ogg")  # Use .ogg for web compatibility
            self.boom_sound = pygame.mixer.Sound("boom.ogg")
            self.win_sound = pygame.mixer.Sound("win.ogg")
        except FileNotFoundError as e:
            print(f"Error loading asset: {e}")
            # Fallback to colored rectangles/silence
            self.gem = pygame.Surface((40, 40))
            self.gem.fill(Colors.BLUE)
            self.mine = pygame.Surface((40, 40))
            self.mine.fill(Colors.RED)
            self.click_sound = pygame.mixer.Sound(pygame.mixer.Sound(buffer=b'\0' * 1000))  # Silent sound
            self.boom_sound = self.click_sound
            self.win_sound = self.click_sound

class MineGemGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Mine & Gem Game")
        self.clock = pygame.time.Clock()
        self.assets = GameAssets()
        self.stats = self._load_stats()
        self.balance = self.stats.get("balance", 1000.0)
        self.high_score = self.stats.get("high_score", 0.0)
        self.sound_enabled = self.stats.get("sound_enabled", True)
        self.leaderboard = self._load_leaderboard()
        self.difficulty = "Medium"
        self.total_games = self.stats.get("total_games", 0)
        self.total_wins = self.stats.get("total_wins", 0)
        self.total_losses = self.stats.get("total_losses", 0)
        self.total_earnings = self.stats.get("total_earnings", 0.0)
        self.promocode_used = self.stats.get("promocode_used", False)
        self.grid_size_index = 1  # Default to 5

    def _load_stats(self) -> Dict:
        """Load game statistics (in-memory for web)."""
        # For web, we'll simulate file loading with defaults since file access is limited
        try:
            if os.path.exists(STATS_FILE):  # Works locally, ignored in browser
                with open(STATS_FILE, "r") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            print("Error loading stats or not available in browser, using defaults.")
        return {
            "balance": 1000.0,
            "high_score": 0.0,
            "sound_enabled": True,
            "total_games": 0,
            "total_wins": 0,
            "total_losses": 0,
            "total_earnings": 0.0,
            "promocode_used": False
        }

    def _save_stats(self) -> None:
        """Save game statistics (in-memory for web)."""
        self.stats = {
            "balance": self.balance,
            "high_score": self.high_score,
            "sound_enabled": self.sound_enabled,
            "total_games": self.total_games,
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "total_earnings": self.total_earnings,
            "promocode_used": self.promocode_used
        }
        try:
            with open(STATS_FILE, "w") as f:  # Works locally, ignored in browser
                json.dump(self.stats, f, indent=4)
        except (IOError, OSError):
            print("Stats not saved (web environment or error).")

    def _load_leaderboard(self) -> deque:
        leaderboard = deque(maxlen=5)
        try:
            if os.path.exists(LEADERBOARD_FILE):  # Works locally
                with open(LEADERBOARD_FILE, "r") as f:
                    for line in f:
                        try:
                            score = float(line.strip())
                            leaderboard.append(score)
                        except ValueError:
                            continue
        except (IOError, OSError):
            print("Leaderboard not loaded (web environment or error).")
        return leaderboard

    def _save_leaderboard(self) -> None:
        try:
            with open(LEADERBOARD_FILE, "w") as f:  # Works locally
                for score in sorted(self.leaderboard, reverse=True):
                    f.write(f"{score:.2f}\n")
        except (IOError, OSError):
            print("Leaderboard not saved (web environment or error).")

    async def show_start_menu(self) -> Tuple[int, int, float]:
        self.screen = pygame.display.set_mode((MENU_WIDTH, MENU_HEIGHT))
        pygame.display.set_caption("Game Setup")

        input_fields = {"Number of Mines": "", "Bet Amount (₹)": "", "Promocode": ""}
        difficulties = {"Easy": 0.5, "Medium": 1.0, "Hard": 1.5}
        field_order = ["Grid Size"] + list(input_fields.keys())
        current_index = 0
        selected = field_order[current_index]
        error_message = ""
        success_message = ""

        while True:
            self.screen.fill(Colors.WHITE)
            y = 50
            for i, field in enumerate(field_order):
                color = Colors.BLUE if field == selected else Colors.BLACK
                text = FONT.render(
                    f"Grid Size: {GRID_OPTIONS[self.grid_size_index]} (G to change)" if field == "Grid Size"
                    else f"{field}: {input_fields[field]}", True, color)
                self.screen.blit(text, (50, y))
                y += 70

            diff_text = FONT.render(f"Difficulty: {self.difficulty} (D to change)", True, Colors.DARK_GRAY)
            self.screen.blit(diff_text, (50, y))
            y += 50

            msg = FONT.render("ENTER to switch/start, TAB to switch, S for sound, P to claim promo", True, Colors.DARK_GRAY)
            self.screen.blit(msg, (50, y + 50))

            if error_message:
                error_text = FONT.render(error_message, True, Colors.RED)
                self.screen.blit(error_text, (50, y + 100))
            if success_message:
                success_text = FONT.render(success_message, True, Colors.GREEN)
                self.screen.blit(success_text, (50, y + 130))

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_TAB:
                        current_index = (current_index + 1) % len(field_order)
                        selected = field_order[current_index]
                        error_message = success_message = ""
                    elif event.key == pygame.K_g and selected == "Grid Size":
                        self.grid_size_index = (self.grid_size_index + 1) % len(GRID_OPTIONS)
                        error_message = success_message = ""
                    elif event.key == pygame.K_d:
                        diff_list = list(difficulties.keys())
                        self.difficulty = diff_list[(diff_list.index(self.difficulty) + 1) % len(diff_list)]
                        error_message = success_message = ""
                    elif event.key == pygame.K_s:
                        self.sound_enabled = not self.sound_enabled
                        pygame.mixer.Sound.set_volume(self.assets.click_sound, 1.0 if self.sound_enabled else 0.0)
                        pygame.mixer.Sound.set_volume(self.assets.boom_sound, 1.0 if self.sound_enabled else 0.0)
                        pygame.mixer.Sound.set_volume(self.assets.win_sound, 1.0 if self.sound_enabled else 0.0)
                        error_message = success_message = ""
                    elif event.key == pygame.K_p and selected == "Promocode":
                        if not self.promocode_used:
                            current_time = datetime.now().strftime("%I:%M %p").lstrip("0")
                            entered_time = input_fields[selected].strip().upper()
                            if entered_time == current_time:
                                self.balance += 500.0
                                self.promocode_used = True
                                success_message = "Promocode claimed! +₹500 added."
                                error_message = ""
                                self._save_stats()
                            else:
                                error_message = "Invalid promocode!"
                                success_message = ""
                        else:
                            error_message = "Promocode already used!"
                            success_message = ""
                    elif event.key == pygame.K_RETURN:
                        if selected in ["Promocode", "Grid Size"]:
                            current_index = (current_index + 1) % len(field_order)
                            selected = field_order[current_index]
                        elif all(input_fields[field] for field in input_fields.keys() if field != "Promocode"):
                            try:
                                grid = GRID_OPTIONS[self.grid_size_index]
                                mines = int(int(input_fields["Number of Mines"]) * difficulties[self.difficulty])
                                bet = float(input_fields["Bet Amount (₹)"])
                                if bet > self.balance:
                                    error_message = "Bet exceeds balance!"
                                    continue
                                if mines >= grid * grid:
                                    error_message = "Too many mines for grid size!"
                                    continue
                                if bet <= 0 or mines <= 0:
                                    error_message = "Bet and mines must be positive!"
                                    continue
                                self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                                pygame.display.set_caption("Mine & Gem Game")
                                return grid, mines, bet
                            except ValueError:
                                error_message = "Invalid input! Use numbers only."
                        else:
                            current_index = (current_index + 1) % len(field_order)
                            selected = field_order[current_index]
                            error_message = success_message = ""
                    elif event.key == pygame.K_BACKSPACE and selected != "Grid Size":
                        input_fields[selected] = input_fields[selected][:-1]
                        error_message = success_message = ""
                    elif (event.unicode.isalnum() or event.unicode in [":", " "]) and selected != "Grid Size":
                        if selected == "Promocode":
                            if event.unicode.isdigit() or event.unicode in [":", " "] or event.unicode.lower() in ["a", "p", "m"]:
                                input_fields[selected] += event.unicode
                        elif selected == "Bet Amount (₹)" and (event.unicode.isdigit() or event.unicode == "."):
                            input_fields[selected] += event.unicode
                        elif event.unicode.isdigit():
                            input_fields[selected] += event.unicode
                        error_message = success_message = ""

            await asyncio.sleep(0)  # Yield control to browser

    async def end_screen(self, result: str, final_balance: float) -> bool:
        self.high_score = max(self.high_score, final_balance)
        self.leaderboard.append(final_balance)
        self._save_leaderboard()

        self.total_games += 1
        if result == "won":
            self.total_wins += 1
            self.total_earnings += (final_balance - self.balance)
        else:
            self.total_losses += 1
        self.balance = final_balance
        self._save_stats()

        while True:
            self.screen.fill(Colors.WHITE)
            title = FONT.render(f"You {'Lost!' if result == 'lost' else 'Won!'}", True,
                                Colors.RED if result == "lost" else Colors.GREEN)
            bal = FONT.render(f"Final Balance: ₹{final_balance:.2f}", True, Colors.BLACK)
            high = FONT.render(f"High Score: ₹{self.high_score:.2f}", True, Colors.DARK_GRAY)
            stats = FONT.render(f"Games: {self.total_games}, Wins: {self.total_wins}, Losses: {self.total_losses}", True, Colors.DARK_GRAY)
            earnings = FONT.render(f"Total Earnings: ₹{self.total_earnings:.2f}", True, Colors.DARK_GRAY)
            tip = FONT.render("Press R to Replay, Q to Quit, L for Leaderboard", True, Colors.DARK_GRAY)

            self.screen.blit(title, (200, 150))
            self.screen.blit(bal, (200, 200))
            self.screen.blit(high, (200, 240))
            self.screen.blit(stats, (150, 280))
            self.screen.blit(earnings, (150, 320))
            self.screen.blit(tip, (150, 360))

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        self.quit_game()
                    elif event.key == pygame.K_r:
                        return True
                    elif event.key == pygame.K_l:
                        await self._show_leaderboard()

            await asyncio.sleep(0)

    async def _show_leaderboard(self) -> None:
        while True:
            self.screen.fill(Colors.WHITE)
            title = FONT.render("Leaderboard", True, Colors.BLUE)
            self.screen.blit(title, (200, 50))
            y = 100
            for i, score in enumerate(sorted(self.leaderboard, reverse=True), 1):
                score_text = FONT.render(f"{i}. ₹{score:.2f}", True, Colors.BLACK)
                self.screen.blit(score_text, (200, y))
                y += 40
            back = FONT.render("Press B to go back", True, Colors.DARK_GRAY)
            self.screen.blit(back, (200, y + 20))
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_b:
                    return

            await asyncio.sleep(0)

    async def game_loop(self, grid_size: int, num_mines: int, bet_amount: float) -> None:
        cell_size = GRID_SIZE // grid_size
        revealed = [[False] * grid_size for _ in range(grid_size)]
        game_over = False

        all_positions = [(r, c) for r in range(grid_size) for c in range(grid_size)]
        mine_positions = set(random.sample(all_positions, num_mines))

        self.balance -= bet_amount
        earnings = 0.0
        multiplier = 1.0
        max_earnings = (grid_size * grid_size - num_mines) * bet_amount * 2.0

        while True:
            self.screen.fill(Colors.WHITE)
            self._draw_grid(grid_size, cell_size, revealed, mine_positions, game_over)
            self._draw_hud(earnings, multiplier)

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                elif event.type == pygame.KEYDOWN and not game_over:
                    if event.key == pygame.K_c:
                        self.balance += earnings
                        if self.sound_enabled:
                            self.assets.win_sound.play()
                        if await self.end_screen("won", self.balance):
                            return
                elif event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                    mx, my = event.pos
                    if mx < GRID_SIZE:
                        row, col = my // cell_size, mx // cell_size
                        if 0 <= row < grid_size and 0 <= col < grid_size and not revealed[row][col]:
                            revealed[row][col] = True
                            if self.sound_enabled:
                                self.assets.click_sound.play()
                            if (row, col) in mine_positions:
                                if self.sound_enabled:
                                    self.assets.boom_sound.play()
                                for r in range(grid_size):
                                    for c in range(grid_size):
                                        revealed[r][c] = True
                                game_over = True
                                self._draw_grid(grid_size, cell_size, revealed, mine_positions, game_over)
                                self._draw_hud(earnings, multiplier)
                                pygame.display.flip()
                                pygame.time.delay(1000)
                                if await self.end_screen("lost", self.balance + earnings):
                                    return
                            else:
                                multiplier += 0.1
                                earnings = min(earnings + bet_amount * multiplier, max_earnings)

            if self._check_game_won(grid_size, revealed, mine_positions) and not game_over:
                self.balance += earnings
                if self.sound_enabled:
                    self.assets.win_sound.play()
                if await self.end_screen("won", self.balance):
                    return

            await asyncio.sleep(0)  # Yield control
            self.clock.tick(FPS)

    def _draw_grid(self, grid_size: int, cell_size: int, revealed: List[List[bool]], 
                   mine_positions: Set[Tuple[int, int]], game_over: bool) -> None:
        mx, my = pygame.mouse.get_pos()
        for row in range(grid_size):
            for col in range(grid_size):
                x, y = col * cell_size, row * cell_size
                rect = pygame.Rect(x, y, cell_size, cell_size)
                color = Colors.YELLOW if rect.collidepoint(mx, my) and not revealed[row][col] and not game_over else Colors.GRAY
                pygame.draw.rect(self.screen, color, rect, border_radius=6)
                pygame.draw.rect(self.screen, Colors.DARK_GRAY, rect, 2, border_radius=6)

                if revealed[row][col] or game_over:
                    center_x = x + (cell_size - 40) // 2
                    center_y = y + (cell_size - 40) // 2
                    image = self.assets.mine if (row, col) in mine_positions else self.assets.gem
                    self.screen.blit(image, (center_x, center_y))

    def _draw_hud(self, earnings: float, multiplier: float) -> None:
        pygame.draw.rect(self.screen, Colors.LIGHT_GRAY, (GRID_SIZE, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT))

        balance_text = FONT.render(f"Balance: ₹{self.balance + earnings:.2f}", True, Colors.BLACK)
        mult_text = FONT.render(f"Multiplier: x{multiplier:.1f}", True, Colors.BLUE)
        tip_text = FONT.render("Press 'C' to Cash Out", True, Colors.DARK_GRAY)
        sound_text = FONT.render(f"Sound: {'On' if self.sound_enabled else 'Off'}", True, Colors.DARK_GRAY)
        stats_text = FONT.render(f"Games: {self.total_games}", True, Colors.DARK_GRAY)
        wins_text = FONT.render(f"Wins: {self.total_wins}", True, Colors.DARK_GRAY)
        losses_text = FONT.render(f"Losses: {self.total_losses}", True, Colors.DARK_GRAY)
        earnings_text = FONT.render(f"Earnings: ₹{self.total_earnings:.2f}", True, Colors.DARK_GRAY)

        sidebar_x = GRID_SIZE + 10
        self.screen.blit(balance_text, (sidebar_x, 10))
        self.screen.blit(mult_text, (sidebar_x, 40))
        self.screen.blit(tip_text, (sidebar_x, 70))
        self.screen.blit(sound_text, (sidebar_x, 100))
        self.screen.blit(stats_text, (sidebar_x, 130))
        self.screen.blit(wins_text, (sidebar_x, 160))
        self.screen.blit(losses_text, (sidebar_x, 190))
        self.screen.blit(earnings_text, (sidebar_x, 220))

    def _check_game_won(self, grid_size: int, revealed: List[List[bool]], 
                        mine_positions: Set[Tuple[int, int]]) -> bool:
        return all(revealed[r][c] or (r, c) in mine_positions 
                   for r in range(grid_size) for c in range(grid_size))

    def quit_game(self) -> None:
        self._save_leaderboard()
        self._save_stats()
        pygame.quit()
        sys.exit()

async def main():
    game = MineGemGame()
    while True:
        grid, mines, bet = await game.show_start_menu()
        await game.game_loop(grid, mines, bet)
        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())