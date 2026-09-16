from .animation import Animation


class AnimationPlayer:
    def __init__(self) -> None:
        self.current_animation: Animation | None = None
        self.frame_index = 0

    def play(self, animation: Animation) -> None:
        self.current_animation = animation
        self.frame_index = 0