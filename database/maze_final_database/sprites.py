# sprites.py
import pygame
import random
from settings import BUTTON_BG_COLOR, BUTTON_SHADOW_COLOR, WHITE, GREEN, RED, YELLOW, BARRIER_COLOR

def load_or_fallback(path: str, size: tuple[int, int], shape: str = "circle", color: tuple[int, int, int] = (255, 255, 255)) -> pygame.Surface:
    """
    Utility function: Tries to load an image, else draws a fallback shape.
    It now correctly handles both PNG (with transparency) and JPG (without).
    """
    try:
        image = pygame.image.load(path)
        # Use .convert_alpha() for PNGs, and the faster .convert() for everything else.
        if path.lower().endswith(".png"):
            image = image.convert_alpha()
        else:
            image = image.convert()
        return pygame.transform.scale(image, size)
    except pygame.error:
        print(f"[Warning] Could not load {path}. Using fallback shape.")
        surf = pygame.Surface(size, pygame.SRCALPHA)
        if shape == "circle":
            pygame.draw.circle(surf, color, (size[0] // 2, size[1] // 2), size[0] // 2)
        elif shape == "rect":
            surf.fill(color)
        return surf

class Ball(pygame.sprite.Sprite):
    """Represents the player's ball in the game."""
    def __init__(self, x: int, y: int, size: tuple[int, int] = (20, 20)): # Reduced size for easier movement
        super().__init__()
        self.image = load_or_fallback("assets/Ball.png", size, shape="circle", color=WHITE)
        self.rect = self.image.get_rect(center=(x, y))
        
        # Shadow setup
        self.shadow_offset = (5, 5)
        shadow_size = (size[0] + 5, size[1] + 5) # Slightly larger shadow
        self.shadow_surface = pygame.Surface(shadow_size, pygame.SRCALPHA)
        pygame.draw.circle(self.shadow_surface, (0, 0, 0, 90), 
                           (shadow_size[0] // 2, shadow_size[1] // 2), 
                           shadow_size[0] // 2)

    def draw_with_shadow(self, screen):
        """Draws the shadow first, then the ball."""
        shadow_pos = (self.rect.x + self.shadow_offset[0], self.rect.y + self.shadow_offset[1])
        screen.blit(self.shadow_surface, shadow_pos)
        screen.blit(self.image, self.rect)

class Hole(pygame.sprite.Sprite):
    """Represents the goal hole in the maze."""
    def __init__(self, x: int, y: int, size: tuple[int, int] = (60, 60)):
        super().__init__()
        self.image = load_or_fallback("assets/Hole.png", size, shape="circle", color=GREEN)
        self.rect = self.image.get_rect(center=(x, y))

class Barrier(pygame.sprite.Sprite):
    """Represents a single wall tile in the maze."""
    def __init__(self, x: int, y: int, width: int, height: int):
        super().__init__()
        self.image = load_or_fallback("assets/Barrier.png", (width, height), shape="rect", color=BARRIER_COLOR)
        self.rect = self.image.get_rect(topleft=(x, y))

class Button:
    """A clickable UI button for menus with a shadow and press effect."""
    def __init__(self, x: int, y: int, width: int, height: int, text: str, font: pygame.font.Font, base_color: tuple, hover_color: tuple, shadow_offset: int = 5):
        self.rect = pygame.Rect(x, y, width, height)
        self.shadow_rect = pygame.Rect(x + shadow_offset, y + shadow_offset, width, height)
        self.text = text
        self.font = font
        self.base_color = base_color
        self.hover_color = hover_color
        self.is_hovered = False
        self.is_pressed = False

    def draw(self, screen: pygame.Surface):
        """Draws the button onto the screen, handling hover and press states."""
        current_rect = self.rect
        if self.is_pressed:
            current_rect = self.shadow_rect

        pygame.draw.rect(screen, BUTTON_SHADOW_COLOR, self.shadow_rect, border_radius=15)
        pygame.draw.rect(screen, BUTTON_BG_COLOR, current_rect, border_radius=15)

        color = self.hover_color if self.is_hovered else self.base_color
        text_surf = self.font.render(self.text, True, color)
        text_rect = text_surf.get_rect(center=current_rect.center)
        screen.blit(text_surf, text_rect)

    def check_hover(self, mouse_pos: tuple[int, int]):
        """Checks if the mouse is over the button."""
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, event: pygame.event.Event) -> bool:
        """Checks for mouse button down and up events to create a 'press' effect."""
        if event.type == pygame.MOUSEBUTTONDOWN and self.is_hovered:
            self.is_pressed = True
            return False
        
        if event.type == pygame.MOUSEBUTTONUP and self.is_pressed:
            self.is_pressed = False
            if self.is_hovered:
                return True
        
        return False

class Particle(pygame.sprite.Sprite):
    """A small particle for visual effects."""
    def __init__(self, x, y, color, size, velocity):
        super().__init__()
        self.image = pygame.Surface((size, size))
        pygame.draw.circle(self.image, color, (size // 2, size // 2), size // 2)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.velocity = pygame.math.Vector2(velocity)
        self.lifespan = 60
        self.alpha = 255

    def update(self):
        self.rect.move_ip(self.velocity)
        self.lifespan -= 1
        
        if self.lifespan < 30:
            self.alpha = max(0, self.alpha - (255 / 30))
            self.image.set_alpha(self.alpha)

        if self.lifespan <= 0:
            self.kill()