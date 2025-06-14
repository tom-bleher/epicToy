#!/usr/bin/env python3
"""
Grid angle analyzer for individual hits from ROOT simulation data.
Shows neighborhood (9x9) pixel grid visualizations around specific hit positions.
Also generates ensemble averages and handles edge cases.
"""

import uproot
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import time
import os
import random

class RandomHitGridGenerator:
    """
    Generator for neighborhood (9x9) grid angle visualizations for random individual hits
    """
    
    def __init__(self, filename):
        self.filename = filename
        self.data = None
        self.detector_params = {}
        self.load_data()
        
    def load_data(self):
        """Load data from ROOT file"""
        try:
            with uproot.open(self.filename) as file:
                # Load detector parameters from TNamed objects
                self.detector_params = {
                    'pixel_size': float(file['GridPixelSize'].member('fTitle')),
                    'pixel_spacing': float(file['GridPixelSpacing'].member('fTitle')), 
                    'pixel_corner_offset': float(file['GridPixelCornerOffset'].member('fTitle')),
                    'detector_size': float(file['GridDetectorSize'].member('fTitle')),
                    'num_blocks_per_side': int(file['GridNumBlocksPerSide'].member('fTitle'))
                }
                
                # Load hit data
                tree = file["Hits"]
                self.data = tree.arrays(library="np")
                
                print(f"Loaded detector parameters: {self.detector_params}")
                print(f"Loaded {len(self.data['TrueX'])} events")
                
        except Exception as e:
            print(f"Error loading data: {e}")
            raise
    
    def plot_single_neighborhood_grid(self, event_idx, save_individual=True, output_dir="", event_type="random"):
        """Plot focused neighborhood (9x9) grid for a single hit"""
        if 'GridNeighborhoodAngles' not in self.data:
            print(f"No neighborhood grid data found for event {event_idx}")
            return None
            
        # Get event data
        hit_x = self.data['TrueX'][event_idx]
        hit_y = self.data['TrueY'][event_idx]
        hit_z = self.data['PosZ'][event_idx]
        pixel_x = self.data['PixelX'][event_idx]
        pixel_y = self.data['PixelY'][event_idx]
        pixel_dist = self.data['PixelTrueDistance'][event_idx]
        pixel_hit = self.data['PixelHit'][event_idx]
        grid_angles = self.data['GridNeighborhoodAngles'][event_idx]
        
        # Reshape 81-element array into 9x9 grid
        # NOTE: The C++ code stores data with di (X direction) as outer loop and dj (Y direction) as inner loop
        # When reshaped as (9,9), we need to transpose to get correct (Y,X) indexing for visualization
        angle_grid = np.array(grid_angles).reshape(9, 9).T  # Transpose to fix coordinate system
        
        # Replace invalid angles (-999.0) with NaN for proper display
        angle_grid[angle_grid == -999.0] = np.nan
        
        # If hit is inside a pixel, all angles should be NaN (correct the Geant4 bug)
        if pixel_hit:
            print(f"  Hit is inside pixel - setting all angles to NaN")
            angle_grid[:] = np.nan
        
        # Get detector parameters
        pixel_size = self.detector_params['pixel_size']
        pixel_spacing = self.detector_params['pixel_spacing']
        
        # Create figure focused on 9x9 grid area
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # Calculate the bounds of the 9x9 grid centered on PixelX, PixelY
        grid_extent = 4.5 * pixel_spacing  # 4.5 pixels in each direction from center
        margin = 0  # No margin around the grid
        
        ax.set_xlim(pixel_x - grid_extent, pixel_x + grid_extent)
        ax.set_ylim(pixel_y - grid_extent, pixel_y + grid_extent)
        ax.set_aspect('equal')
        
        # Remove axis ticks and labels
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Calculate valid angle range for colormap
        valid_angles = angle_grid[~np.isnan(angle_grid)]
        if len(valid_angles) > 0:
            vmin, vmax = np.min(valid_angles), np.max(valid_angles)
        else:
            vmin, vmax = 0, 1
            
        # Create colormap for angles
        cmap = plt.cm.viridis
        
        # First, draw the colored blocks (grid cells) behind the pixels
        for i in range(9):
            for j in range(9):
                # Calculate pixel position relative to center (PixelX, PixelY is center)
                rel_x = (j - 4) * pixel_spacing  # j maps to x direction, offset from center
                rel_y = (i - 4) * pixel_spacing  # i maps to y direction, offset from center
                
                # Block center position (same as pixel center)
                block_center_x = pixel_x + rel_x
                block_center_y = pixel_y + rel_y
                
                # Calculate block corners for drawing (blocks are pixel_spacing sized)
                block_corner_x = block_center_x - pixel_spacing/2
                block_corner_y = block_center_y - pixel_spacing/2
                
                # Get angle value for this grid position
                angle_value = angle_grid[i, j]
                
                if not np.isnan(angle_value):
                    # Color block based on angle value
                    normalized_angle = (angle_value - vmin) / (vmax - vmin) if vmax > vmin else 0
                    color = cmap(normalized_angle)
                    
                    # Draw colored block (grid cell)
                    block_rect = patches.Rectangle((block_corner_x, block_corner_y), 
                                                 pixel_spacing, pixel_spacing,
                                                 linewidth=0.5, edgecolor='black', 
                                                 facecolor=color, alpha=0.7)
                    ax.add_patch(block_rect)
                    
                    # Position text below the pixel within the block
                    text_y = block_center_y - pixel_size/2 - 0.08  # Further below the pixel
                    
                    # Add angle text in the block below the pixel
                    ax.text(block_center_x, text_y, f'{angle_value:.1f}°',
                           ha='center', va='center', fontsize=10, 
                           color='black', weight='bold')
                else:
                    # Invalid angle - draw block with different style
                    block_rect = patches.Rectangle((block_corner_x, block_corner_y), 
                                                 pixel_spacing, pixel_spacing,
                                                 linewidth=0.5, edgecolor='red', 
                                                 facecolor='lightgray', alpha=0.5)
                    ax.add_patch(block_rect)
                    
                    # Position text below the pixel within the block
                    text_y = block_center_y - pixel_size/2 - 0.08  # Further below the pixel
                    
                    # Add "N/A" text
                    ax.text(block_center_x, text_y, 'N/A',
                           ha='center', va='center', fontsize=9, 
                           color='red', weight='bold')
        
        # Now draw the pixels on top with uniform fill color
        for i in range(9):
            for j in range(9):
                # Calculate pixel position relative to center (PixelX, PixelY is center)
                rel_x = (j - 4) * pixel_spacing  # j maps to x direction, offset from center
                rel_y = (i - 4) * pixel_spacing  # i maps to y direction, offset from center
                
                # Actual pixel center position
                pixel_center_x = pixel_x + rel_x
                pixel_center_y = pixel_y + rel_y
                
                # Calculate pixel corners for drawing
                pixel_corner_x = pixel_center_x - pixel_size/2
                pixel_corner_y = pixel_center_y - pixel_size/2
                
                # Draw pixel with uniform fill and edge color
                pixel_rect = patches.Rectangle((pixel_corner_x, pixel_corner_y), 
                                             pixel_size, pixel_size,
                                             linewidth=1.5, edgecolor='black', 
                                             facecolor='black', alpha=1.0)
                ax.add_patch(pixel_rect)
        
        # Mark the actual hit position
        ax.plot(hit_x, hit_y, 'ro', markersize=8, markeredgewidth=4, 
                label=f'Hit Position ({hit_x:.2f}, {hit_y:.2f})')
        
        # Mark the center pixel position (PixelX, PixelY)
        #ax.plot(pixel_x, pixel_y, 'ko', markersize=12, 
                #markerfacecolor='yellow', markeredgecolor='black', markeredgewidth=3,
                #label=f'Center Pixel ({pixel_x:.2f}, {pixel_y:.2f})')
        
        # Draw grid lines to separate blocks clearly (thinner lines)
        for i in range(10):  # 10 lines for 9 blocks
            # Vertical lines
            x_line = pixel_x + (i - 4.5) * pixel_spacing
            ax.axvline(x=x_line, color='black', linewidth=0.5, alpha=0.8)
            
            # Horizontal lines  
            y_line = pixel_y + (i - 4.5) * pixel_spacing
            ax.axhline(y=y_line, color='black', linewidth=0.5, alpha=0.8)
        
        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, label=r'$\alpha^{\circ}\mathrm{deg}$')
        cbar.ax.tick_params(labelsize=10)
        
        # Add concise scientific title
        hit_type = "Inside Pixel" if pixel_hit else "Outside Pixel"
        
        # Count invalid positions for edge cases
        invalid_positions = np.sum(angle_grid == -999.0) if not pixel_hit else 0
        
        if event_type == "edge-case" and invalid_positions > 0:
            title = f"9×9 Grid Angular Analysis: Event {event_idx} (Edge Case)\n" \
                    f"Hit: ({hit_x:.2f}, {hit_y:.2f}) mm, {invalid_positions}/81 positions outside detector"
        elif event_type == "inside-pixel":
            title = f"9×9 Grid Angular Analysis: Event {event_idx} (Inside Pixel)\n" \
                    f"Hit: ({hit_x:.2f}, {hit_y:.2f}) mm, Distance: {pixel_dist:.3f} mm"
        else:
            title = f"9×9 Grid Angular Analysis: Event {event_idx} (Random)\n" \
                    f"Hit: ({hit_x:.2f}, {hit_y:.2f}) mm, Distance: {pixel_dist:.3f} mm"
        
        ax.set_title(title, fontsize=12, fontweight='bold', pad=15)
        
        plt.tight_layout()
        
        # Save individual plot if requested
        if save_individual:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f'event_{event_idx}_9x9_grid_{timestamp}.png'
            if output_dir:
                filename = os.path.join(output_dir, filename)
            
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Event {event_idx} saved to {filename}")
        
        plt.show()
        
        # Print statistics for this event
        if len(valid_angles) > 0:
            print(f"  Event {event_idx}: {len(valid_angles)} valid angles, "
                  f"range {np.min(valid_angles):.1f}° to {np.max(valid_angles):.1f}°, "
                  f"center: {angle_grid[4, 4]:.1f}°, distance: {pixel_dist:.3f} mm")
        
        return fig, ax, angle_grid
    
    def plot_mean_neighborhood_grid(self, save_plot=True, output_dir=""):
        """Plot mean neighborhood (9x9) grid averaged across all non-inside-pixel events"""
        if 'GridNeighborhoodAngles' not in self.data:
            print("No neighborhood grid data found for mean calculation")
            return None
            
        # Find all non-inside-pixel events
        pixel_hit = self.data['PixelHit']
        non_inside_pixel_mask = ~pixel_hit
        non_inside_pixel_indices = np.where(non_inside_pixel_mask)[0]
        
        if len(non_inside_pixel_indices) == 0:
            print("No non-inside-pixel events found for mean calculation")
            return None
            
        print(f"Calculating mean across {len(non_inside_pixel_indices)} non-inside-pixel events")
        
        # Collect all angle grids for non-inside-pixel events
        all_angle_grids = []
        valid_event_count = 0
        
        for event_idx in non_inside_pixel_indices:
            grid_angles = self.data['GridNeighborhoodAngles'][event_idx]
            angle_grid = np.array(grid_angles).reshape(9, 9).T  # Transpose to fix coordinate system
            
            # Replace invalid angles (-999.0) with NaN
            angle_grid[angle_grid == -999.0] = np.nan
            
            # Skip events that have all NaN values
            if not np.all(np.isnan(angle_grid)):
                all_angle_grids.append(angle_grid)
                valid_event_count += 1
        
        if len(all_angle_grids) == 0:
            print("No valid angle data found for mean calculation")
            return None
            
        print(f"Using {valid_event_count} events with valid angle data for mean calculation")
        
        # Calculate mean, ignoring NaN values
        angle_grids_array = np.array(all_angle_grids)
        mean_angle_grid = np.nanmean(angle_grids_array, axis=0)
        
        # Calculate some representative positions for the plot
        # Use the first non-inside-pixel event for positioning reference
        ref_event_idx = non_inside_pixel_indices[0]
        pixel_x = self.data['PixelX'][ref_event_idx]
        pixel_y = self.data['PixelY'][ref_event_idx]
        
        # Get detector parameters
        pixel_size = self.detector_params['pixel_size']
        pixel_spacing = self.detector_params['pixel_spacing']
        
        # Create figure focused on neighborhood (9x9) grid area
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # Calculate the bounds of the 9x9 grid centered on reference position
        grid_extent = 4.5 * pixel_spacing
        
        ax.set_xlim(pixel_x - grid_extent, pixel_x + grid_extent)
        ax.set_ylim(pixel_y - grid_extent, pixel_y + grid_extent)
        ax.set_aspect('equal')
        
        # Remove axis ticks and labels
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Calculate valid angle range for colormap
        valid_mean_angles = mean_angle_grid[~np.isnan(mean_angle_grid)]
        if len(valid_mean_angles) > 0:
            vmin, vmax = np.min(valid_mean_angles), np.max(valid_mean_angles)
        else:
            vmin, vmax = 0, 1
            
        # Create colormap for angles
        cmap = plt.cm.viridis
        
        # Draw the colored blocks (grid cells) behind the pixels
        for i in range(9):
            for j in range(9):
                # Calculate pixel position relative to center
                rel_x = (j - 4) * pixel_spacing
                rel_y = (i - 4) * pixel_spacing
                
                # Block center position
                block_center_x = pixel_x + rel_x
                block_center_y = pixel_y + rel_y
                
                # Calculate block corners for drawing
                block_corner_x = block_center_x - pixel_spacing/2
                block_corner_y = block_center_y - pixel_spacing/2
                
                # Get mean angle value for this grid position
                mean_angle_value = mean_angle_grid[i, j]
                
                if not np.isnan(mean_angle_value):
                    # Color block based on mean angle value
                    normalized_angle = (mean_angle_value - vmin) / (vmax - vmin) if vmax > vmin else 0
                    color = cmap(normalized_angle)
                    
                    # Draw colored block (grid cell)
                    block_rect = patches.Rectangle((block_corner_x, block_corner_y), 
                                                 pixel_spacing, pixel_spacing,
                                                 linewidth=0.5, edgecolor='black', 
                                                 facecolor=color, alpha=0.7)
                    ax.add_patch(block_rect)
                    
                    # Position text below the pixel within the block
                    text_y = block_center_y - pixel_size/2 - 0.08
                    
                    # Add mean angle text in the block below the pixel
                    ax.text(block_center_x, text_y, f'{mean_angle_value:.1f}°',
                           ha='center', va='center', fontsize=10, 
                           color='black', weight='bold')
                else:
                    # No valid data for this position - draw block with different style
                    block_rect = patches.Rectangle((block_corner_x, block_corner_y), 
                                                 pixel_spacing, pixel_spacing,
                                                 linewidth=0.5, edgecolor='red', 
                                                 facecolor='lightgray', alpha=0.5)
                    ax.add_patch(block_rect)
                    
                    # Position text below the pixel within the block
                    text_y = block_center_y - pixel_size/2 - 0.08
                    
                    # Add "N/A" text
                    ax.text(block_center_x, text_y, 'N/A',
                           ha='center', va='center', fontsize=9, 
                           color='red', weight='bold')
        
        # Draw the pixels on top with uniform fill color
        for i in range(9):
            for j in range(9):
                # Calculate pixel position relative to center
                rel_x = (j - 4) * pixel_spacing
                rel_y = (i - 4) * pixel_spacing
                
                # Actual pixel center position
                pixel_center_x = pixel_x + rel_x
                pixel_center_y = pixel_y + rel_y
                
                # Calculate pixel corners for drawing
                pixel_corner_x = pixel_center_x - pixel_size/2
                pixel_corner_y = pixel_center_y - pixel_size/2
                
                # Draw pixel with uniform fill and edge color
                pixel_rect = patches.Rectangle((pixel_corner_x, pixel_corner_y), 
                                             pixel_size, pixel_size,
                                             linewidth=1.5, edgecolor='black', 
                                             facecolor='black', alpha=1.0)
                ax.add_patch(pixel_rect)
        
        # Draw grid lines to separate blocks clearly
        for i in range(10):  # 10 lines for 9 blocks
            # Vertical lines
            x_line = pixel_x + (i - 4.5) * pixel_spacing
            ax.axvline(x=x_line, color='black', linewidth=0.5, alpha=0.8)
            
            # Horizontal lines  
            y_line = pixel_y + (i - 4.5) * pixel_spacing
            ax.axhline(y=y_line, color='black', linewidth=0.5, alpha=0.8)
        
        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, label=r'Mean $\alpha^{\circ}\mathrm{deg}$')
        cbar.ax.tick_params(labelsize=10)
        
        # Add title to distinguish from individual plots
        title = f'Mean Angular Distribution: Neighborhood (9x9) Grid Analysis\n' \
                f'Ensemble Average (N = {valid_event_count} events, excluding inside-pixel hits)'
        ax.set_title(title, fontsize=12, fontweight='bold', pad=15)
        
        plt.tight_layout()
        
        # Save plot if requested
        if save_plot:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f'mean_neighborhood_grid_{valid_event_count}_events_{timestamp}.png'
            if output_dir:
                filename = os.path.join(output_dir, filename)
            
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Mean grid plot saved to {filename}")
        
        plt.show()
        
        # Print statistics
        if len(valid_mean_angles) > 0:
            print(f"  Mean grid: {len(valid_mean_angles)} valid positions, "
                  f"range {np.min(valid_mean_angles):.1f}° to {np.max(valid_mean_angles):.1f}°, "
                  f"center mean: {mean_angle_grid[4, 4]:.1f}°")
        
        return fig, ax, mean_angle_grid, valid_event_count
    
    def generate_random_hits_individual(self, num_events=3, save_plots=True, output_dir="", seed=None, include_mean=True, include_edge_case=True):
        """Create individual neighborhood (9x9) grid visualizations for N random hits and optionally a mean plot"""
        if 'GridNeighborhoodAngles' not in self.data:
            print("No neighborhood grid data found")
            return None
            
        # Set random seed for reproducibility if provided
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
            
        # Select N random events
        total_events = len(self.data['TrueX'])
        if num_events > total_events:
            print(f"Requested {num_events} events, but only {total_events} available. Using all events.")
            num_events = total_events
            
        random_events = random.sample(range(total_events), num_events)
        random_events.sort()  # Sort for easier reference
        
        print(f"Selected {num_events} random events: {random_events}")
        
        # Find an event where hit was inside pixel or closest to it
        inside_pixel_event = self.find_inside_pixel_event()
        
        # Find an edge case event where neighborhood (9x9) grid is incomplete
        edge_case_event = None
        if include_edge_case:
            edge_case_event = self.find_edge_case_event()
        
        # Combine all events, avoiding duplicates
        all_events = random_events.copy()
        
        if inside_pixel_event is not None and inside_pixel_event not in all_events:
            print(f"Adding inside-pixel event: {inside_pixel_event}")
            all_events.append(inside_pixel_event)
            
        if edge_case_event is not None and edge_case_event not in all_events:
            print(f"Adding edge case event: {edge_case_event}")
            all_events.append(edge_case_event)
            
        # Create output directory if specified
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
        
        # Process each event individually
        results = []
        for i, event_idx in enumerate(all_events):
            event_type = "random"
            if event_idx == inside_pixel_event:
                event_type = "inside-pixel"
            elif event_idx == edge_case_event:
                event_type = "edge-case"
                
            print(f"\nProcessing {event_type} event {event_idx} ({i+1}/{len(all_events)})...")
            fig, ax, angle_grid = self.plot_single_neighborhood_grid(event_idx, 
                                                           save_individual=save_plots, 
                                                           output_dir=output_dir,
                                                           event_type=event_type)
            results.append((event_idx, fig, ax, angle_grid))
        
        # Generate mean plot if requested
        if include_mean:
            print(f"\nGenerating mean plot...")
            fig, ax, mean_angle_grid, valid_event_count = self.plot_mean_neighborhood_grid(save_plot=save_plots, 
                                                                                output_dir=output_dir)
            results.append((-1, fig, ax, mean_angle_grid))
        
        print(f"\n" + "="*60)
        print(f"PROCESSING COMPLETE")
        print(f"="*60)
        print(f"Generated {len(all_events)} individual neighborhood (9x9) grid visualizations")
        print(f"Random events: {random_events}")
        if inside_pixel_event is not None:
            print(f"Inside-pixel/closest event: {inside_pixel_event}")
        if edge_case_event is not None:
            print(f"Edge case event: {edge_case_event}")
        if include_mean:
            print(f"Mean plot: averaged across all non-inside-pixel events")
        if save_plots:
            if output_dir:
                print(f"Plots saved to directory: {output_dir}")
            else:
                print(f"Plots saved to current directory")
        
        return results, all_events
    
    def find_edge_case_event(self):
        """Find an event where the hit is near the detector edge so neighborhood (9x9) grid is incomplete"""
        if 'GridNeighborhoodAngles' not in self.data:
            print("GridNeighborhoodAngles data not available for edge case search")
            return None
            
        # Get detector parameters
        detector_size = self.detector_params['detector_size']
        pixel_spacing = self.detector_params['pixel_spacing']
        
        # Calculate how close to edge a hit needs to be for incomplete neighborhood (9x9) grid
        grid_half_extent = 4 * pixel_spacing  # 4 pixels from center to edge of neighborhood grid
        edge_threshold = detector_size/2 - grid_half_extent
        
        print(f"Detector size: {detector_size} mm")
        print(f"Grid half extent: {grid_half_extent} mm") 
        print(f"Edge threshold: {edge_threshold} mm from detector center")
        
        # Find events where hit is close to any edge
        hit_x = self.data['TrueX']
        hit_y = self.data['TrueY']
        
        # Calculate distance from detector center and edges
        dist_from_center = np.sqrt(hit_x**2 + hit_y**2)
        
        # Check which events have hits near edges (close to detector boundary)
        near_edge_mask = dist_from_center > edge_threshold
        near_edge_indices = np.where(near_edge_mask)[0]
        
        if len(near_edge_indices) == 0:
            print("No events found with hits near detector edges")
            # If no clear edge cases, find the event closest to the edge
            farthest_idx = np.argmax(dist_from_center)
            farthest_distance = dist_from_center[farthest_idx]
            print(f"Using event {farthest_idx} with maximum distance from center: {farthest_distance:.3f} mm")
            return int(farthest_idx)
        
        # From near-edge events, find one that actually has incomplete grid data
        best_edge_event = None
        max_incomplete_count = 0
        
        for event_idx in near_edge_indices:
            grid_angles = self.data['GridNeighborhoodAngles'][event_idx]
            angle_grid = np.array(grid_angles).reshape(9, 9).T  # Transpose to fix coordinate system
            
            # Count incomplete/invalid positions (should be -999.0 for out-of-bounds)
            incomplete_count = np.sum(angle_grid == -999.0)
            
            if incomplete_count > max_incomplete_count:
                max_incomplete_count = incomplete_count
                best_edge_event = event_idx
                
        if best_edge_event is not None:
            hit_x_val = hit_x[best_edge_event]
            hit_y_val = hit_y[best_edge_event]
            distance = dist_from_center[best_edge_event]
            print(f"Found edge case event {best_edge_event} at ({hit_x_val:.3f}, {hit_y_val:.3f}) mm")
            print(f"Distance from center: {distance:.3f} mm, incomplete positions: {max_incomplete_count}/81")
            return int(best_edge_event)
        else:
            # Fallback to the first near-edge event
            event_idx = near_edge_indices[0]
            hit_x_val = hit_x[event_idx]
            hit_y_val = hit_y[event_idx]
            distance = dist_from_center[event_idx]
            print(f"Using near-edge event {event_idx} at ({hit_x_val:.3f}, {hit_y_val:.3f}) mm")
            print(f"Distance from center: {distance:.3f} mm")
            return int(event_idx)

    def find_inside_pixel_event(self):
        """Find an event where the hit was inside a pixel, or the closest one"""
        if 'PixelHit' not in self.data or 'PixelTrueDistance' not in self.data:
            print("PixelHit or PixelTrueDistance data not available")
            return None
            
        pixel_hit = self.data['PixelHit']
        pixel_dist = self.data['PixelTrueDistance']
        
        # First, check if there are any events where hit is inside pixel
        inside_pixel_indices = np.where(pixel_hit == True)[0]
        
        if len(inside_pixel_indices) > 0:
            # Use the first inside-pixel event
            event_idx = inside_pixel_indices[0]
            print(f"Found {len(inside_pixel_indices)} events with hits inside pixels")
            print(f"Using event {event_idx} (hit inside pixel)")
            return int(event_idx)
        else:
            # Find the event with minimum distance (closest to being inside pixel)
            min_dist_idx = np.argmin(pixel_dist)
            min_distance = pixel_dist[min_dist_idx]
            print(f"No events with hits inside pixels found")
            print(f"Using event {min_dist_idx} with minimum distance: {min_distance:.4f} mm")
            return int(min_dist_idx)

def create_random_hits_plots(root_filename, num_events=1, output_dir="", seed=42, include_mean=True, include_edge_case=True):
    """
    Convenience function to create N random hits plots from ROOT file
    
    Parameters:
    -----------
    root_filename : str
        Path to ROOT file containing neighborhood (9x9) grid data
    num_events : int, optional
        Number of random events to visualize (default: 1)
    output_dir : str, optional
        Directory to save plots (default: current directory)
    seed : int, optional
        Random seed for reproducible selection of events
    include_mean : bool, optional
        Whether to include a mean plot of all non-inside-pixel events (default: True)
    include_edge_case : bool, optional
        Whether to include an edge case where neighborhood (9x9) grid is incomplete (default: True)
    
    Returns:
    --------
    tuple : (results, selected_events)
    """
    generator = RandomHitGridGenerator(root_filename)
    return generator.generate_random_hits_individual(num_events=num_events, 
                                                   save_plots=True, 
                                                   output_dir=output_dir, 
                                                   seed=seed,
                                                   include_mean=include_mean,
                                                   include_edge_case=include_edge_case)

if __name__ == "__main__":
    # Configuration parameters
    NUM_EVENTS = 3  # Change this to control number of random events to visualize
    OUTPUT_DIR = "neighborhood_grid_plots"  # Directory to save plots (empty string for current directory)
    RANDOM_SEED = 42  # For reproducible results
    INCLUDE_MEAN = True  # Whether to include mean plot of all non-inside-pixel events
    INCLUDE_EDGE_CASE = True  # Whether to include edge case where neighborhood (9x9) grid is incomplete
    
    # Default ROOT file (can be changed)
    root_file = "epicToyOutput.root"
    
    # Check if file exists
    if not os.path.exists(root_file):
        print(f"Error: ROOT file '{root_file}' not found!")
        print("Make sure you have run the Geant4 simulation first.")
        exit(1)
    
    print("="*60)
    print(f"GENERATING {NUM_EVENTS} RANDOM HITS NEIGHBORHOOD (9x9) GRIDS")
    if INCLUDE_MEAN:
        print("+ MEAN GRID OF ALL NON-INSIDE-PIXEL EVENTS")
    if INCLUDE_EDGE_CASE:
        print("+ EDGE CASE WHERE NEIGHBORHOOD (9x9) GRID IS INCOMPLETE")
    print("="*60)
    
    try:
        # Generate the visualization
        results, selected_events = create_random_hits_plots(root_file, 
                                                          num_events=NUM_EVENTS,
                                                          output_dir=OUTPUT_DIR,
                                                          seed=RANDOM_SEED,
                                                          include_mean=INCLUDE_MEAN,
                                                          include_edge_case=INCLUDE_EDGE_CASE)
        
        print("\n" + "="*60)
        print("VISUALIZATION COMPLETE")
        print("="*60)
        print(f"Generated {NUM_EVENTS} individual neighborhood (9x9) grid plots for events: {selected_events}")
        if INCLUDE_MEAN:
            print("Generated 1 mean neighborhood (9x9) grid plot averaged across all non-inside-pixel events")
        if INCLUDE_EDGE_CASE:
            print("Generated 1 edge case neighborhood (9x9) grid plot where grid extends beyond detector")
        print("Each event is displayed as a separate plot focused on its neighborhood (9x9) grid area.")
        
    except Exception as e:
        print(f"Error generating visualization: {e}")
        import traceback
        traceback.print_exc() 