import math
import random
from typing import Tuple, List, Optional

import arcade
import pymunk
from pyglet.gl import GL_NEAREST


WINDOW_HEIGHT = 600
WINDOW_WIDTH = 800
TRACE_LENGTH = 4000


class Ball(arcade.SpriteCircle):

    def __init__(self,
                 mass: int,
                 physics_engine: arcade.PymunkPhysicsEngine,
                 position: Tuple[float, float],
                 body_type=pymunk.Body.DYNAMIC,
                 **kwargs
                 ):
        super().__init__(radius=2*int(math.sqrt(mass)), **kwargs)
        self.position = position
        self.color = kwargs.get('color')
        self.constraint: Optional[pymunk.Constraint] = None
        physics_engine.add_sprite(
            self,
            mass=mass,
            friction=0.2 * mass**2,
            body_type=body_type
        )
        self.traces = [position]*TRACE_LENGTH

    def pymunk_moved(self, physics_engine, dx, dy, d_angle):
        super().pymunk_moved(physics_engine, dx, dy, d_angle)
        self.traces = self.traces[1:] + [self.position]


class MyView(arcade.View):

    def __init__(self):
        super().__init__()
        self.physics_engine = arcade.PymunkPhysicsEngine((0, -250))
        self.balls = arcade.SpriteList()

        self.col_detector = arcade.SpriteCircle(1, arcade.csscolor.BLACK)
        self.attached: Optional[pymunk.Body] = None
        self.attached_sprite: Optional[Ball] = None
        self.current_ball_mass: int = 10
        self.running: bool = False

        self.center_pin = Ball(1,
                               self.physics_engine,
                               (WINDOW_WIDTH/2, WINDOW_HEIGHT/2),
                               body_type=pymunk.Body.STATIC,
                               color=arcade.csscolor.BLACK,
                               )
        self.balls.append(self.center_pin)

        ball_masses = [10, 15, 20]
        ball_positions = [(500, 300), (600, 300), (650, 300)]
        self.create_balls(ball_masses, ball_positions)

    def join_balls(self, ball_a, ball_b):
        body_a = self.physics_engine.get_physics_object(ball_a).body
        body_b = self.physics_engine.get_physics_object(ball_b).body if type(ball_b) == Ball else ball_b
        constraint = pymunk.PinJoint(body_a, body_b)
        ball_a.constraint = constraint
        self.physics_engine.space.add(constraint)

    def create_ball(self, mass: int, position: Tuple[float, float], **kwargs):
        ball = Ball(
            mass,
            self.physics_engine,
            position,
            color=(random.randrange(255), random.randrange(255), random.randrange(255)),
            **kwargs
        )
        self.balls.append(ball)

    def create_balls(self, masses: List[int], positions: List[Tuple[float, float]], **kwargs):
        assert len(masses) == len(positions), ValueError('Length of masses and positions must be equal')
        [self.create_ball(masses[i], positions[i], **kwargs) for i in range(len(masses))]
        last_ball = self.center_pin
        for ball in self.balls:
            if ball is self.center_pin:
                continue
            self.join_balls(last_ball, ball)
            last_ball = ball

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        self.col_detector.position = x, y
        if self.attached_sprite is not None:
            self.attached_sprite.position = x, y

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        super().on_mouse_press(x, y, button, modifiers)
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.col_detector.position = x, y
            clicked_sprites = arcade.check_for_collision_with_list(self.col_detector, self.balls)
            if len(clicked_sprites) > 0:
                self.attached = self.physics_engine.get_physics_object(clicked_sprites[0]).body
                self.attached_sprite = clicked_sprites[0]
        elif button == arcade.MOUSE_BUTTON_RIGHT:
            self.create_ball(self.current_ball_mass, (x, y))
            self.join_balls(self.balls[-2], self.balls[-1])
        elif button == arcade.MOUSE_BUTTON_MIDDLE:
            self.col_detector.position = x, y
            clicked_sprite: List[Ball] = arcade.check_for_collision_with_list(self.col_detector, self.balls)
            if len(clicked_sprite) > 0:
                clicked_sprite: Ball = clicked_sprite[0]
                index = self.balls.index(clicked_sprite)
                if index != 0:
                    if clicked_sprite.constraint is not None:
                        self.join_balls(self.balls[index-1], clicked_sprite.constraint.b)
                        self.physics_engine.space.remove(clicked_sprite.constraint)
                    self.balls.remove(clicked_sprite)
                    self.physics_engine.remove_sprite(clicked_sprite)

    def on_mouse_scroll(self, x: int, y: int, scroll_x: int, scroll_y: int):
        self.current_ball_mass += scroll_y
        self.current_ball_mass = max(self.current_ball_mass, 1)

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int):
        if self.attached is not None:
            index: int = self.balls.index(self.attached_sprite)
            previous_ball: Ball = self.balls[index-1]
            self.physics_engine.space.remove(previous_ball.constraint)
            self.join_balls(previous_ball, self.attached_sprite)
            next_constraint = self.attached_sprite.constraint
            if next_constraint is not None:
                self.physics_engine.space.remove(next_constraint)
                self.join_balls(self.attached_sprite, next_constraint.b)
            self.attached = None
            self.attached_sprite = None

    def on_key_release(self, _symbol: int, _modifiers: int):
        if _symbol == arcade.key.SPACE:
            self.running = not self.running

    def on_draw(self):
        arcade.start_render()
        pos = self.center_pin.position
        for ball in self.balls:
            ball: Ball
            try:
                arcade.draw_line_strip(ball.traces, ball.color)
            except AttributeError:
                pass
            arcade.draw_line(*pos, *ball.position, arcade.csscolor.WHITE)
            pos = ball.position
        self.balls.draw(filter=GL_NEAREST)
        if not self.running:
            arcade.draw_text(
                'Press [Space] to continue simulation',
                WINDOW_WIDTH/2,
                WINDOW_HEIGHT/2,
                anchor_y='center',
                anchor_x='center',
                color=arcade.csscolor.WHITE
            )
            arcade.draw_text(
                'Left-click to move balls\n' +
                'Right-click to place balls\n' +
                'Middle-click to remove balls\n' +
                'Scroll to adjust mass of new balls',
                10,
                WINDOW_HEIGHT,
                multiline=True,
                width=400
            )
            arcade.draw_circle_outline(
                *self.col_detector.position,
                2*int(math.sqrt(self.current_ball_mass)),
                arcade.csscolor.RED,
                num_segments=10
            )

    def on_update(self, delta_time: float):
        super().on_update(delta_time)
        if self.attached is not None:
            self.attached.update_position(self.attached, delta_time)
            self.attached.position = self.col_detector.position
        if self.running:
            self.physics_engine.step(delta_time)


def main():
    window: arcade.Window = arcade.Window(title='Pendulum Stuff', width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
    view: arcade.View = MyView()
    window.show_view(view)
    # window.background_color = 128, 128, 128, 255
    arcade.run()


if __name__ == '__main__':
    main()
    