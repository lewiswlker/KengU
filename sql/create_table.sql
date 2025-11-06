-- Create courses table
CREATE TABLE IF NOT EXISTS courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_name VARCHAR(255) NOT NULL UNIQUE,
    update_time_moodle DATETIME DEFAULT NULL,
    update_time_exambase DATETIME DEFAULT NULL,
    INDEX idx_course_name (course_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create user_courses table (foreign key constraint)
CREATE TABLE IF NOT EXISTS user_courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    course_id INT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_course_id (course_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
