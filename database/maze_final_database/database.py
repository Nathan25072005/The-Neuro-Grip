# database.py
import mysql.connector
from mysql.connector import pooling
import os
import json
import statistics
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Database Connection Pool ---
connection_pool = None # Initialize to None
try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="neurogrip_pool",
        pool_size=5,
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    print("Successfully created database connection pool.")
except Exception as e:
    print(f"FATAL: Error creating connection pool: {e}")
    print("Please check your MySQL server is running and your .env file is correct.")
    exit() # Fails fast if the database can't be reached on startup

def init_db():
    """
    Initializes the database by creating tables if they don't already exist.
    This function should be run once using the db_setup.py script.
    """
    conn = None
    cursor = None
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        print("Running initial database setup...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Players (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                gender VARCHAR(50),
                age INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_player (name, gender, age)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS GameSessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                player_id INT NOT NULL,
                session_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES Players(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS LevelResults (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id INT NOT NULL,
                level_name VARCHAR(50) NOT NULL,
                duration_seconds FLOAT,
                collision_count INT,
                max_fsr INT,
                min_fsr_move INT,
                fsr_readings_move JSON,
                path_points JSON,
                shortest_path_length FLOAT,
                FOREIGN KEY (session_id) REFERENCES GameSessions(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        print("Database tables are ready.")
    except Exception as e:
        print(f"Error during database initialization: {e}")
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

# --- Player Management ---
def add_player(name, gender, age):
    """Adds a player if they don't exist, returns their ID."""
    conn = None
    cursor = None
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        # Use LOWER() for case-insensitive lookup
        query = "SELECT id FROM Players WHERE LOWER(name) = LOWER(%s) AND gender = %s AND age = %s"
        cursor.execute(query, (name, gender, age))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        else:
            insert_query = "INSERT INTO Players (name, gender, age) VALUES (%s, %s, %s)"
            cursor.execute(insert_query, (name, gender, int(age)))
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"Error in add_player: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

# --- Game Session Management ---
def create_game_session(player_id):
    """Creates a new game session and returns its ID."""
    conn = None
    cursor = None
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO GameSessions (player_id) VALUES (%s)", (player_id,))
        conn.commit()
        session_id = cursor.lastrowid
        print(f"Started new game session with ID: {session_id}")
        return session_id
    except Exception as e:
        print(f"Error in create_game_session: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

# --- Results Management ---
def save_level_result(session_id, metrics):
    """Saves the metrics from a completed level."""
    conn = None
    cursor = None
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO LevelResults (
                session_id, level_name, duration_seconds, collision_count,
                max_fsr, min_fsr_move, fsr_readings_move, path_points, shortest_path_length
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        fsr_json = json.dumps(metrics.get("FSR_Readings_Move", []))
        path_json = json.dumps(metrics.get("Path_Points", []))
        values = (
            session_id, metrics.get("LevelName"), metrics.get("Duration"),
            metrics.get("Collision_Count"), metrics.get("Max_FSR"), metrics.get("Min_FSR_Move"),
            fsr_json, path_json, metrics.get("Shortest_Path_Length")
        )
        cursor.execute(sql, values)
        conn.commit()
    except Exception as e:
        print(f"Error in save_level_result: {e}")
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

def get_session_results(session_id):
    """Retrieves all results for a session ID to generate a report."""
    conn = None
    cursor = None
    results = []
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM LevelResults WHERE session_id = %s ORDER BY id ASC", (session_id,))
        rows = cursor.fetchall()
        for row in rows:
            results.append({
                "LevelName": row['level_name'],
                "Duration": row['duration_seconds'],
                "Collision_Count": row['collision_count'],
                "Max_FSR": row['max_fsr'],
                "Min_FSR_Move": row['min_fsr_move'],
                "FSR_Readings_Move": json.loads(row['fsr_readings_move']),
                "Path_Points": json.loads(row['path_points']),
                "Shortest_Path_Length": row['shortest_path_length']
            })
        return results
    except Exception as e:
        print(f"Error fetching session results: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

# --- NEW: Historical Data Function ---
def get_player_history(player_id):
    """
    Retrieves and calculates a historical summary of a player's performance.
    """
    conn = None
    cursor = None
    summary = {
        "total_sessions": 0,
        "total_levels_played": 0,
        "total_playtime_seconds": 0,
        "avg_collisions_per_level": 0,
        "avg_grip_cov": 0, # Average Coefficient of Variation for grip stability
        "levels_by_difficulty": {}
    }

    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        # SQL query to get all level results for a player by joining the tables
        sql = """
            SELECT 
                r.level_name,
                r.duration_seconds,
                r.collision_count,
                r.fsr_readings_move,
                s.id as session_id
            FROM LevelResults r
            JOIN GameSessions s ON r.session_id = s.id
            WHERE s.player_id = %s
        """
        cursor.execute(sql, (player_id,))
        results = cursor.fetchall()

        if not results:
            return summary # Return the empty summary if no records are found

        # --- Process the results in Python ---
        total_collisions = 0
        all_level_covs = []
        unique_sessions = set()
        levels_by_difficulty = {}

        for row in results:
            unique_sessions.add(row['session_id'])
            summary["total_playtime_seconds"] += row['duration_seconds']
            total_collisions += row['collision_count']
            
            # Count levels played by difficulty
            level_name = row['level_name']
            levels_by_difficulty[level_name] = levels_by_difficulty.get(level_name, 0) + 1

            # Calculate CoV for this level's grip data
            fsr_readings = json.loads(row['fsr_readings_move'])
            if len(fsr_readings) > 1:
                mean_fsr = statistics.mean(fsr_readings)
                stdev_fsr = statistics.stdev(fsr_readings)
                cov = (stdev_fsr / mean_fsr) * 100 if mean_fsr > 0 else 0
                all_level_covs.append(cov)
        
        # --- Final calculations ---
        summary["total_sessions"] = len(unique_sessions)
        summary["total_levels_played"] = len(results)
        summary["levels_by_difficulty"] = levels_by_difficulty
        if summary["total_levels_played"] > 0:
            summary["avg_collisions_per_level"] = total_collisions / summary["total_levels_played"]
        if all_level_covs:
            summary["avg_grip_cov"] = statistics.mean(all_level_covs)
            
        return summary

    except Exception as e:
        print(f"Error in get_player_history: {e}")
        return None # Return None on error
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()