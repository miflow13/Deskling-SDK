from collections.abc import Callable
from pathlib import Path

from desktoppet.animation import AnimationPlayer
from desktoppet.behavior import BehaviorScheduler, RoamController
from desktoppet.config.manifest import PetManifest
from desktoppet.interaction import DragController
from desktoppet.movement import Direction, MovementController, Position, Size
from desktoppet.platforms.base import PlatformBackend

from .events import EventBus
from .state import StateController


class Pet:
    """Composition root for the reusable pet engine.

    Learning note:
        A composition root is the place where separate pieces are created and
        wired together. `Pet` does not try to *be* the animation system, state
        machine, movement system, drag system, etc. Instead, it HAS those
        components and coordinates them.

        PetManifest -> Pet -> engine components -> PlatformBackend

    The manifest provides the pet's configuration/data. The backend provides
    platform-specific capabilities such as drawing a frame and moving a window.
    The core Pet class connects those two worlds without importing GTK.
    """

    def __init__(self, manifest: PetManifest, backend: PlatformBackend) -> None:
        # These are the two major inputs to the runtime:
        # 1. manifest = what this pet is configured to do
        # 2. backend = how this operating system displays/moves the pet
        self.manifest = manifest
        self.backend = backend

        # Pet owns small focused components rather than putting every job into
        # one giant class. This is composition: Pet HAS an EventBus,
        # AnimationPlayer, StateController, MovementController, etc.
        self.events = EventBus()
        self.player = AnimationPlayer()
        self.states = StateController(manifest.pet.default_state, manifest.transitions)
        self._walking_direction: Direction | None = None

        scale = manifest.pet.scale
        size = Size(manifest.pet.width * scale, manifest.pet.height * scale)
        speed = manifest.roam_behavior.speed_px_s if manifest.roam_behavior else 80.0
        self.movement = MovementController(backend.get_bounds(), size, speed_px_s=speed)
        self.drag = DragController(self.movement)

        self.scheduler: BehaviorScheduler | None = None
        if manifest.idle_behavior is not None:
            config = manifest.idle_behavior
            self.scheduler = BehaviorScheduler(
                config.actions,
                min_delay_ms=config.min_delay_ms,
                max_delay_ms=config.max_delay_ms,
            )

        self.roam: RoamController | None = None
        if manifest.roam_behavior is not None:
            config = manifest.roam_behavior
            self.roam = RoamController(
                min_delay_ms=config.min_delay_ms,
                max_delay_ms=config.max_delay_ms,
                min_walk_ms=config.min_walk_ms,
                max_walk_ms=config.max_walk_ms,
            )

        # Once all components exist, place the window and start the configured
        # default animation. This is the point where the blueprint becomes live.
        self.backend.set_position(self.movement.position)
        self.play(manifest.pet.default_animation)

    @classmethod
    def from_path(cls, path: str | Path, backend: PlatformBackend) -> "Pet":
        from desktoppet.config import load_manifest

        return cls(load_manifest(path), backend)

    @property
    def state(self) -> str:
        return self.states.current_state

    @property
    def position(self) -> Position:
        return self.movement.position

    def on(self, event_name: str) -> Callable:
        return self.events.on(event_name)

    def set_state(self, target: str) -> None:
        previous = self.states.transition(target)
        if previous != target:
            self.events.emit("state.changed", previous=previous, current=target)

    def play(self, animation_name: str, *, state: str | None = None) -> None:
        animation = self.manifest.animations.get(animation_name)
        if animation is None:
            raise KeyError(f"Unknown animation: {animation_name}")
        if state is not None and state != self.state:
            self.set_state(state)
        self.player.play(animation)
        frame = self.player.current_frame
        if frame is not None:
            self.backend.show_frame(frame.path)
        self.events.emit("animation.started", animation=animation_name)

    def react(self, animation_name: str) -> None:
        """Interrupt normal behavior and play a one-shot reaction animation."""
        if self.roam is not None and self.roam.is_walking:
            self.roam.cancel()
        self._walking_direction = None

        # A reaction may arrive while another interruptible state (such as
        # walking) is active. If that state cannot go directly to "reaction",
        # route through the configured default state first.
        if self.state != "reaction" and not self.states.can_transition("reaction"):
            default_state = self.manifest.pet.default_state
            if self.state != default_state and self.states.can_transition(default_state):
                self.set_state(default_state)

        if self.state == "reaction" or self.states.can_transition("reaction"):
            self.play(animation_name, state="reaction")
        else:
            # Custom state graphs may intentionally omit a reaction state.
            # The animation can still play without forcing an illegal transition.
            self.play(animation_name)

    def handle_click(self, clicks: int, *, x: float = 0.0, y: float = 0.0) -> None:
        """Publish click events and run the configured click reaction.

        GTK (or another future platform adapter) reports the raw gesture here.
        The core owns the pet-specific meaning of that gesture, which keeps
        platform input separate from personality/configuration.
        """
        if clicks <= 0:
            raise ValueError("clicks must be greater than zero")

        self.events.emit("pet.clicked", clicks=clicks, x=x, y=y)

        interaction = self.manifest.interaction
        if clicks >= 2:
            self.events.emit("pet.double_clicked", x=x, y=y)
            animation_name = (
                interaction.double_click_animation if interaction is not None else None
            )
        else:
            animation_name = interaction.click_animation if interaction is not None else None

        # A drag owns the pointer interaction until release. The GTK adapter also
        # suppresses the release-click generated by a completed drag.
        if animation_name is not None and self.state != "dragging":
            self.react(animation_name)

    def tick(self, delta_ms: int) -> None:
        previous_frame = self.player.current_frame
        self.player.tick(delta_ms)
        current_frame = self.player.current_frame

        if current_frame is not None and current_frame is not previous_frame:
            self.backend.show_frame(current_frame.path)
            self.events.emit(
                "animation.frame",
                animation=self.player.current_animation.name if self.player.current_animation else None,
                frame_index=self.player.frame_index,
            )

        if self.player.just_finished:
            finished_name = self.player.current_animation.name if self.player.current_animation else None
            self.events.emit("animation.finished", animation=finished_name)
            if self.state != self.manifest.pet.default_state and self.states.can_transition(
                self.manifest.pet.default_state
            ):
                self.set_state(self.manifest.pet.default_state)
                self.play(self.manifest.pet.default_animation)

        self._tick_roam(delta_ms)

        if self.scheduler is not None:
            action = self.scheduler.tick(
                delta_ms,
                active=self.state == self.manifest.pet.default_state,
            )
            if action is not None and action in self.manifest.animations:
                if self.states.can_transition("reaction"):
                    self.react(action)
                else:
                    self.play(action)
                self.events.emit("behavior.triggered", action=action)

    def move(self, direction: Direction, delta_ms: int) -> Position:
        self._begin_walk(direction)
        position = self.movement.move(direction, delta_ms / 1000.0)
        self.backend.set_position(position)
        self.events.emit("movement.moved", direction=direction.value, position=position)
        return position

    def stop_moving(self) -> None:
        previous_direction = self._walking_direction
        self._walking_direction = None
        default_state = self.manifest.pet.default_state
        if self.state != default_state and self.states.can_transition(default_state):
            self.set_state(default_state)
        self.play(self.manifest.pet.default_animation)
        self.events.emit(
            "movement.stopped",
            direction=previous_direction.value if previous_direction else None,
            position=self.position,
        )

    def drag_start(self, pointer_x: float, pointer_y: float) -> None:
        if self.roam is not None and self.roam.is_walking:
            self.roam.cancel()
        self._walking_direction = None
        if self.state != "dragging":
            self.set_state("dragging")
        self.drag.start(pointer_x, pointer_y)
        self.events.emit("drag.started", position=self.position)

    def drag_move(self, pointer_x: float, pointer_y: float) -> Position:
        position = self.drag.update(pointer_x, pointer_y)
        self.backend.set_position(position)
        self.events.emit("drag.moved", position=position)
        return position

    def drag_end(self) -> Position:
        position = self.drag.end()
        self.events.emit("drag.ended", position=position)
        default_state = self.manifest.pet.default_state
        if self.states.can_transition(default_state):
            self.set_state(default_state)
            self.play(self.manifest.pet.default_animation)
        return position

    def _begin_walk(self, direction: Direction) -> None:
        if self.state != "walking" and self.states.can_transition("walking"):
            self.set_state("walking")

        if self._walking_direction is direction:
            return

        self._walking_direction = direction
        animation_name = self._walk_animation_for(direction)
        if animation_name is not None:
            self.play(animation_name)
        self.events.emit("movement.started", direction=direction.value, position=self.position)

    def _walk_animation_for(self, direction: Direction) -> str | None:
        config = self.manifest.roam_behavior
        if config is None:
            return None
        if direction is Direction.LEFT:
            return config.left_animation
        if direction is Direction.RIGHT:
            return config.right_animation
        return None

    def _tick_roam(self, delta_ms: int) -> None:
        roam = self.roam
        if roam is None:
            return

        default_state = self.manifest.pet.default_state
        event = roam.tick(
            delta_ms,
            active=self.state in {default_state, "walking"},
        )

        if event is not None and event.kind == "stopped":
            if self.state == "walking":
                self.stop_moving()
            return

        if event is not None and event.kind == "started" and event.direction is not None:
            self._begin_walk(event.direction)
            self.events.emit("behavior.triggered", action="roam")

        direction = roam.direction
        if direction is None or self.state != "walking":
            return

        before = self.position
        after = self.move(direction, delta_ms)
        if after == before:
            self.events.emit("movement.edge_reached", direction=direction.value, position=after)
            direction = roam.reverse()
            self.move(direction, delta_ms)
