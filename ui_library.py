import pygame as pg

class Button:
    def __init__(self, x, y, width, height, base_color, hover_color, text_color, text, font):
        self.rect = pg.Rect(x, y, width, height)
        self.base_color = base_color
        self.hover_color = hover_color
        self.current_color = base_color
        self.text_surf = font.render(text, True, text_color)
        self.text_rect = self.text_surf.get_rect()
        self.text_rect.center = self.rect.center

    def update(self, mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            self.current_color = self.hover_color
        else:
            self.current_color = self.base_color

    def handle_event(self, event, mouse_pos, action):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(mouse_pos):
                action()

    def draw(self, screen):
        pg.draw.rect(screen, self.current_color, self.rect)
        screen.blit(self.text_surf, self.text_rect)
