#!/usr/bin/env python3
"""
Visualize the exploration plan execution with GUI controls
"""

import yaml
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Rectangle, Circle
from matplotlib.lines import Line2D
from matplotlib.widgets import Button, Slider
import numpy as np
import re

def parse_plan_file(filename='sas_plan'):
    """Parse the plan file to extract actions"""
    actions = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('(') and line.endswith(')'):
                    # Parse action
                    match = re.match(r'\((\w+)\s+(\w+)\s+(\w+)(?:\s+(\w+))?\)', line)
                    if match:
                        action_type = match.group(1)
                        if action_type == 'move':
                            actions.append({
                                'type': 'move',
                                'robot': match.group(2),
                                'from': match.group(3),
                                'to': match.group(4)
                            })
                        elif action_type == 'observe':
                            actions.append({
                                'type': 'observe',
                                'robot': match.group(2),
                                'location': match.group(3)
                            })
    except FileNotFoundError:
        print(f"Plan file {filename} not found")
    return actions

def load_config(filename='terrain_config.yaml'):
    """Load the terrain configuration"""
    with open(filename, 'r') as f:
        return yaml.safe_load(f)

def location_to_coords(loc_str):
    """Convert location string (e.g., 'l23') to grid coordinates"""
    match = re.match(r'l(\d)(\d)', loc_str)
    if match:
        row = int(match.group(1))
        col = int(match.group(2))
        return (row, col)
    return None

class PlanVisualizer:
    def __init__(self, config, actions):
        self.config = config
        self.actions = actions
        self.grid_size = config['grid_size']
        
        # Animation state
        self.current_step = -1
        self.is_playing = False
        self.animation_speed = 1.5  # seconds per frame
        self.animation = None
        
        # Initialize robot positions
        self.robot_positions = {}
        self.robot_colors = {}
        self.initial_positions = {}
        colors = ['blue', 'green', 'red', 'purple', 'orange']
        
        # Create case-insensitive mapping
        self.robot_name_map = {}
        for i, (robot, props) in enumerate(config['robots'].items()):
            start_row, start_col = props['start']
            self.robot_positions[robot] = (start_row, start_col)
            self.initial_positions[robot] = (start_row, start_col)
            self.robot_colors[robot] = colors[i % len(colors)]
            # Map both upper and lower case
            self.robot_name_map[robot.lower()] = robot
            self.robot_name_map[robot.upper()] = robot
        
        # Track explored locations
        self.explored = set()
        
        # Parse terrain map
        self.terrain_map = {}
        default_terrain = config['terrain_map'].get('default', 'normal')
        
        for row in range(1, self.grid_size + 1):
            for col in range(1, self.grid_size + 1):
                self.terrain_map[(row, col)] = default_terrain
        
        # Apply special terrains
        for key, terrain in config['terrain_map'].get('special', {}).items():
            if isinstance(key, str):
                # Parse string format "[row, col]"
                match = re.match(r'\[(\d+),\s*(\d+)\]', key)
                if match:
                    row, col = int(match.group(1)), int(match.group(2))
                    self.terrain_map[(row, col)] = terrain
            else:
                row, col = key
                self.terrain_map[(row, col)] = terrain
        
        # Parse special observations
        self.special_obs = {}
        for key, robots in config.get('special_observations', {}).items():
            if isinstance(key, str):
                match = re.match(r'\[(\d+),\s*(\d+)\]', key)
                if match:
                    row, col = int(match.group(1)), int(match.group(2))
                    self.special_obs[(row, col)] = robots
            else:
                self.special_obs[key] = robots
        
        # Terrain colors
        self.terrain_colors = {
            'normal': '#90EE90',      # Light green
            'rocky': '#A0522D',       # Brown
            'restricted': '#FFB6C1',  # Light pink
            'water': '#87CEEB',       # Sky blue
            'cliff': '#696969'        # Dark gray
        }
        
        # Action list text objects
        self.action_texts = []
        
        # Setup figure with GUI
        self.setup_gui()
        
    def setup_action_list(self):
        """Setup the action list display"""
        self.action_ax.text(0.5, 0.98, 'Action Plan', 
                           ha='center', va='top', fontsize=14, weight='bold',
                           transform=self.action_ax.transAxes)
        
        # Create text for each action
        max_display = min(25, len(self.actions))  # Limit display to avoid crowding
        y_start = 0.94
        y_step = 0.035
        
        for i in range(max_display):
            if i < len(self.actions):
                action = self.actions[i]
                if action['type'] == 'move':
                    text = f"{i+1}. Move {action['robot']} {action['from']}→{action['to']}"
                else:
                    text = f"{i+1}. {action['robot']} observe {action['location']}"
            else:
                text = ""
            
            y_pos = y_start - (i * y_step)
            txt_obj = self.action_ax.text(0.05, y_pos, text,
                                         transform=self.action_ax.transAxes,
                                         fontsize=10, va='top')
            self.action_texts.append(txt_obj)
        
        # Add scroll indicator if needed
        if len(self.actions) > max_display:
            self.action_ax.text(0.5, 0.02, f'... and {len(self.actions) - max_display} more actions',
                               ha='center', va='bottom', fontsize=9, style='italic',
                               transform=self.action_ax.transAxes)
        
    def setup_gui(self):
        """Setup the figure with control panel"""
        # Create figure with GridSpec for layout
        self.fig = plt.figure(figsize=(16, 10))
        
        # Create grid layout: main plot, action list on right, controls at bottom
        gs = self.fig.add_gridspec(10, 12, hspace=0.3, wspace=0.3)
        
        # Main plot area (left side)
        self.ax = self.fig.add_subplot(gs[0:9, 0:8])
        
        # Action list area (right side)
        self.action_ax = self.fig.add_subplot(gs[0:9, 8:12])
        self.action_ax.axis('off')
        
        # Control panel spans the bottom row
        control_height = 0.08
        
        # Create buttons with proper positioning
        button_width = 0.08
        button_height = 0.04
        button_y = 0.02
        
        # Play/Pause button
        self.play_ax = plt.axes([0.05, button_y, button_width, button_height])
        self.play_button = Button(self.play_ax, 'Play', color='lightgreen')
        self.play_button.on_clicked(self.toggle_play)
        
        # Step Backward button
        self.step_back_ax = plt.axes([0.14, button_y, button_width*0.8, button_height])
        self.step_backward_button = Button(self.step_back_ax, '◄', color='lightblue')
        self.step_backward_button.on_clicked(self.step_backward)
        
        # Step Forward button
        self.step_fwd_ax = plt.axes([0.22, button_y, button_width*0.8, button_height])
        self.step_forward_button = Button(self.step_fwd_ax, '►', color='lightblue')
        self.step_forward_button.on_clicked(self.step_forward)
        
        # Reset button
        self.reset_ax = plt.axes([0.30, button_y, button_width*0.8, button_height])
        self.reset_button = Button(self.reset_ax, 'Reset', color='lightcoral')
        self.reset_button.on_clicked(self.reset)
        
        # Speed slider
        self.speed_ax = plt.axes([0.42, button_y, 0.20, button_height*0.8])
        self.speed_slider = Slider(
            self.speed_ax,
            'Speed', 0.5, 5.0, valinit=self.animation_speed,
            valstep=0.5
        )
        self.speed_slider.on_changed(self.update_speed)
        
        # Step counter text
        self.step_text = self.fig.text(0.65, button_y + button_height/2, 
                                      f'Step: 0/{len(self.actions)}', 
                                      fontsize=12, weight='bold', va='center')
        
        # Setup action list display
        self.setup_action_list()
        
    def draw_grid(self):
        """Draw the grid with terrain - (1,1) at bottom-left"""
        self.ax.clear()
        self.ax.set_xlim(0, self.grid_size)
        self.ax.set_ylim(0, self.grid_size)
        self.ax.set_aspect('equal')
        
        # Draw terrain
        for row in range(1, self.grid_size + 1):
            for col in range(1, self.grid_size + 1):
                terrain = self.terrain_map.get((row, col), 'normal')
                color = self.terrain_colors.get(terrain, '#FFFFFF')
                
                # Now (1,1) is at bottom-left, (3,3) at top-right
                plot_row = row - 1
                plot_col = col - 1
                
                rect = Rectangle((plot_col, plot_row), 1, 1, 
                               facecolor=color, edgecolor='black', linewidth=2)
                self.ax.add_patch(rect)
                
                # Add location label
                self.ax.text(plot_col + 0.5, plot_row + 0.9, f'({row},{col})',
                           ha='center', va='top', fontsize=8, weight='bold')
                
                # Mark explored locations
                if (row, col) in self.explored:
                    self.ax.text(plot_col + 0.5, plot_row + 0.1, '✓',
                               ha='center', va='bottom', fontsize=16, color='darkgreen')
                
                # Mark special observations
                if (row, col) in self.special_obs:
                    robots = self.special_obs[(row, col)]
                    obs_text = f"[{','.join(robots)} only]"
                    self.ax.text(plot_col + 0.5, plot_row + 0.5, obs_text,
                               ha='center', va='center', fontsize=9,
                               bbox=dict(boxstyle="round,pad=0.3", facecolor='yellow', alpha=0.7))
        
        # Draw robots (handle multiple robots in same cell)
        # Group robots by position
        robots_at_pos = {}
        for robot, (row, col) in self.robot_positions.items():
            pos_key = (row, col)
            if pos_key not in robots_at_pos:
                robots_at_pos[pos_key] = []
            robots_at_pos[pos_key].append(robot)
        
        # Draw robots
        for (row, col), robots in robots_at_pos.items():
            plot_row = row - 0.5
            plot_col = col - 0.5
            
            if len(robots) == 1:
                # Single robot - draw normally
                robot = robots[0]
                canonical_robot = self.robot_name_map.get(robot, robot)
                color = self.robot_colors.get(canonical_robot, 'gray')
                
                circle = Circle((plot_col, plot_row), 0.3, 
                              color=color, 
                              ec='black', linewidth=2)
                self.ax.add_patch(circle)
                self.ax.text(plot_col, plot_row, canonical_robot,
                           ha='center', va='center', fontsize=12, 
                           weight='bold', color='white')
            else:
                # Multiple robots - arrange them in the cell
                n_robots = len(robots)
                
                # Calculate positions for multiple robots
                if n_robots == 2:
                    # Side by side
                    offsets = [(-0.2, 0), (0.2, 0)]
                elif n_robots == 3:
                    # Triangle arrangement
                    offsets = [(-0.2, -0.15), (0.2, -0.15), (0, 0.15)]
                elif n_robots == 4:
                    # Square arrangement
                    offsets = [(-0.15, -0.15), (0.15, -0.15), (-0.15, 0.15), (0.15, 0.15)]
                else:
                    # Circle arrangement for more robots
                    angle_step = 2 * np.pi / n_robots
                    radius = 0.25
                    offsets = [(radius * np.cos(i * angle_step), 
                               radius * np.sin(i * angle_step)) 
                              for i in range(n_robots)]
                
                # Draw each robot
                for i, robot in enumerate(robots):
                    canonical_robot = self.robot_name_map.get(robot, robot)
                    color = self.robot_colors.get(canonical_robot, 'gray')
                    
                    offset_x, offset_y = offsets[i]
                    circle = Circle((plot_col + offset_x, plot_row + offset_y), 0.2, 
                                  color=color, 
                                  ec='black', linewidth=2)
                    self.ax.add_patch(circle)
                    self.ax.text(plot_col + offset_x, plot_row + offset_y, canonical_robot,
                               ha='center', va='center', fontsize=10, 
                               weight='bold', color='white')
        
        # Grid lines
        for i in range(self.grid_size + 1):
            self.ax.axhline(i, color='black', linewidth=1)
            self.ax.axvline(i, color='black', linewidth=1)
        
        # Axis labels
        self.ax.set_xlabel('Column', fontsize=12)
        self.ax.set_ylabel('Row', fontsize=12)
        
        # Set ticks
        self.ax.set_xticks(np.arange(0.5, self.grid_size, 1))
        self.ax.set_yticks(np.arange(0.5, self.grid_size, 1))
        self.ax.set_xticklabels(range(1, self.grid_size + 1))
        self.ax.set_yticklabels(range(1, self.grid_size + 1))
        
        # Legend - position it better
        legend_elements = []
        for terrain, color in self.terrain_colors.items():
            if any(t == terrain for t in self.terrain_map.values()):
                legend_elements.append(patches.Patch(facecolor=color, 
                                                   edgecolor='black', 
                                                   label=terrain.capitalize()))
        
        # Add robot legend
        for robot, color in self.robot_colors.items():
            legend_elements.append(Line2D([0], [0], marker='o', color='w', 
                                        markerfacecolor=color, markersize=10,
                                        label=f'Robot {robot}'))
        
        self.ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.02, 0.5))
        
        # Title
        if self.current_step >= 0 and self.current_step < len(self.actions):
            action = self.actions[self.current_step]
            if action['type'] == 'move':
                title = f"Step {self.current_step + 1}: {action['robot']} moves from {action['from']} to {action['to']}"
            else:
                title = f"Step {self.current_step + 1}: {action['robot']} observes {action['location']}"
        else:
            title = "Initial State"
        
        self.ax.set_title(title, fontsize=14, weight='bold')
        
    def update_action_list(self):
        """Update the action list to highlight current action"""
        # Calculate visible range
        max_display = min(25, len(self.actions))
        
        # Determine scroll position to keep current action visible
        if self.current_step >= 0:
            # Calculate window to show current action
            window_start = max(0, min(self.current_step - 5, len(self.actions) - max_display))
        else:
            window_start = 0
        
        # Update each text object
        for i, txt_obj in enumerate(self.action_texts):
            action_idx = window_start + i
            
            if action_idx < len(self.actions):
                action = self.actions[action_idx]
                if action['type'] == 'move':
                    text = f"{action_idx+1}. Move {action['robot']} {action['from']}→{action['to']}"
                else:
                    text = f"{action_idx+1}. {action['robot']} observe {action['location']}"
                
                # Highlight current action
                if action_idx == self.current_step:
                    txt_obj.set_text(f"▶ {text}")
                    txt_obj.set_weight('bold')
                    txt_obj.set_color('red')
                    txt_obj.set_fontsize(11)
                else:
                    txt_obj.set_text(f"  {text}")
                    txt_obj.set_weight('normal')
                    txt_obj.set_color('black')
                    txt_obj.set_fontsize(10)
            else:
                txt_obj.set_text("")
        
    def execute_action(self, action):
        """Execute a single action"""
        if action['type'] == 'move':
            # Map robot name to canonical form
            robot = action['robot']
            canonical_robot = self.robot_name_map.get(robot, robot)
            
            to_coords = location_to_coords(action['to'])
            if to_coords and canonical_robot in self.robot_positions:
                self.robot_positions[canonical_robot] = to_coords
            elif to_coords:
                # Handle case where robot isn't in our mapping
                self.robot_positions[robot] = to_coords
                
        elif action['type'] == 'observe':
            loc_coords = location_to_coords(action['location'])
            if loc_coords:
                self.explored.add(loc_coords)
    
    def animate(self, frame):
        """Animation function"""
        # Only update if we're playing or manually stepping
        if self.is_playing or frame == 0:
            if frame > 0 and self.current_step < len(self.actions) - 1:
                self.current_step += 1
                self.execute_action(self.actions[self.current_step])
            
        self.draw_grid()
        return []
    
    def toggle_play(self, event=None):
        """Toggle play/pause"""
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_button.label.set_text('Pause')
            self.play_button.color = 'lightcoral'
            # Start animation if at the end
            if self.current_step >= len(self.actions) - 1:
                self.reset(None)
            # Create new animation if needed
            if not hasattr(self, 'animation') or self.animation is None:
                self.create_animation()
            self.animation.resume()
        else:
            self.play_button.label.set_text('Play')
            self.play_button.color = 'lightgreen'
            if hasattr(self, 'animation') and self.animation is not None:
                self.animation.pause()
        plt.draw()
    
    def step_forward(self, event=None):
        """Step forward one action"""
        if self.current_step < len(self.actions) - 1:
            self.current_step += 1
            self.execute_action(self.actions[self.current_step])
            self.draw_grid()
            plt.draw()
    
    def step_backward(self, event=None):
        """Step backward one action"""
        if self.current_step >= 0:
            # Reset to initial state and replay up to current_step - 1
            target_step = self.current_step - 1
            self.reset(None)
            for i in range(target_step + 1):
                self.execute_action(self.actions[i])
            self.current_step = target_step
            self.draw_grid()
            plt.draw()
    
    def reset(self, event=None):
        """Reset to initial state"""
        self.current_step = -1
        self.explored = set()
        # Reset robot positions
        for robot, pos in self.initial_positions.items():
            self.robot_positions[robot] = pos
        self.draw_grid()
        plt.draw()
    
    def update_speed(self, val):
        """Update animation speed"""
        self.animation_speed = val
        if self.animation:
            # Convert speed to interval (milliseconds)
            self.animation.interval = int(1000 / val)
    
    def create_animation(self):
        """Create the animation object"""
        self.animation = FuncAnimation(
            self.fig, self.animate, 
            frames=len(self.actions) + 1,
            interval=int(1000 / self.animation_speed),
            repeat=False, blit=False
        )
        if not self.is_playing:
            self.animation.pause()
    
    def run_interactive(self):
        """Run the interactive visualization"""
        # Initial draw
        self.draw_grid()
        
        # Create animation but start paused
        self.create_animation()
        
        # Adjust layout to prevent overlap
        plt.subplots_adjust(bottom=0.10, right=0.98, left=0.02, top=0.98)
        plt.show()
    
    def save_frames(self, output_dir='plan_frames'):
        """Save individual frames as images"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Reset to initial state
        self.reset()
        
        # Initial state
        self.draw_grid()
        plt.savefig(f'{output_dir}/frame_00_initial.png', bbox_inches='tight', dpi=150)
        
        # Execute each action
        for i, action in enumerate(self.actions):
            self.current_step = i
            self.execute_action(action)
            self.draw_grid()
            
            if action['type'] == 'move':
                filename = f"frame_{i+1:02d}_move_{action['robot']}_{action['from']}_to_{action['to']}.png"
            else:
                filename = f"frame_{i+1:02d}_observe_{action['robot']}_{action['location']}.png"
            
            plt.savefig(f'{output_dir}/{filename}', bbox_inches='tight', dpi=150)
        
        print(f"Saved {len(self.actions) + 1} frames to {output_dir}/")

def main():
    """Main function"""
    import sys
    
    # Load configuration
    config = load_config('terrain_config.yaml')
    
    # Parse plan
    actions = parse_plan_file('sas_plan')
    
    if not actions:
        print("No actions found in plan file")
        return
    
    print(f"Loaded {len(actions)} actions from plan")
    
    # Create visualizer
    viz = PlanVisualizer(config, actions)
    
    if '--save-frames' in sys.argv:
        # Save individual frames
        viz.save_frames()
    else:
        # Run interactive visualization
        print("\n=== Interactive Plan Visualizer ===")
        print("Controls:")
        print("  • Play/Pause: Start/stop animation")
        print("  • Step >: Step forward one action")
        print("  • < Step: Step backward one action")
        print("  • Reset: Return to initial state")
        print("  • Speed slider: Adjust animation speed")
        print("\nClose window to exit")
        
        viz.run_interactive()

if __name__ == "__main__":
    main()