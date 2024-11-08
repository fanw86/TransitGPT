import os
import plotly.graph_objects as go
import pandas as pd

def save_map(map_obj, viz_dir, timestamp, index):
    try:
        map_path = f"{viz_dir}/{timestamp}_{index+1}_map.html"
        map_obj.save(map_path)
        return map_path
    except Exception as e:
        print(f"Error saving map: {str(e)}")
        return None

def save_plot(plot_obj, viz_dir, timestamp, index):
    try:
        plot_path = f"{viz_dir}/{timestamp}_{index+1}_plot.png"
        plot_obj.write_image(plot_path, scale=3)
        return plot_path
    except Exception as e:
        print(f"Error saving plot: {str(e)}")
        return None

def save_dataframe(df, viz_dir, timestamp, index):
    try:
        dataframe_path = f"{viz_dir}/{timestamp}_{index+1}_dataframe.csv"
        df.to_csv(dataframe_path, index=False)
        return dataframe_path
    except Exception as e:
        print(f"Error saving dataframe: {str(e)}")
        return None