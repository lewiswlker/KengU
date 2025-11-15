-- 创建 users 表
CREATE TABLE IF NOT EXISTS `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_email` varchar(100) NOT NULL,
  `pwd` varchar(255) DEFAULT '',
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_email` (`user_email`),
  KEY `idx_user_email` (`user_email`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 创建 courses 表
CREATE TABLE IF NOT EXISTS `courses` (
  `id` int NOT NULL AUTO_INCREMENT,
  `course_name` varchar(255) NOT NULL,
  `update_time_moodle` datetime DEFAULT NULL,
  `update_time_exambase` datetime DEFAULT NULL,
  `course_id` int NOT NULL,
  PRIMARY KEY (`id`,`course_id`) USING BTREE,
  UNIQUE KEY `course_name` (`course_name`),
  UNIQUE KEY `idx_course_id_unique` (`course_id`),
  KEY `idx_course_name` (`course_name`)
) ENGINE=InnoDB AUTO_INCREMENT=48 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 创建 user_courses 表
CREATE TABLE IF NOT EXISTS `user_courses` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `course_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_course_id` (`course_id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 创建 assignment 表
CREATE TABLE IF NOT EXISTS `assignment` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `description` text,
  `course_id` int DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `due_date` datetime DEFAULT NULL,
  `max_score` decimal(5,2) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `status` enum('pending','completed','overdue') DEFAULT 'pending',
  `assignment_type` enum('homework','quiz','project','exam','essay') DEFAULT 'homework',
  `instructions` text,
  `attachment_path` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `course_id` (`course_id`),
  CONSTRAINT `assignment_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `courses` (`course_id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 创建 study_sessions 表
CREATE TABLE IF NOT EXISTS `study_sessions` (
  `session_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint unsigned DEFAULT NULL,
  `start_time` datetime NOT NULL,
  `duration_minutes` int NOT NULL DEFAULT '0',
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`session_id`),
  KEY `idx_study_sessions_assignment_id` (`assignment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert mock user
INSERT INTO `users` (`user_email`, `pwd`) VALUES ('u3665467@connect.hku.hk', 'mock_password');

-- Insert mock courses
INSERT INTO `courses` (`course_name`, `update_time_moodle`, `update_time_exambase`, `course_id`) VALUES
('COMP7103 Data mining [Section 1C, 2025]', '2025-11-13 10:00:00', '2025-11-13 10:00:00', 127998),
('COMP7104 Advanced database systems [Section 1A, 2025]', '2025-11-13 10:00:00', '2025-11-13 10:00:00', 128003),
('COMP7607 Natural language processing [Section 1A, 2025]', '2025-11-13 10:00:00', '2025-11-13 10:00:00', 127958),
('COMP7404 Computational intelligence and machine learning [Section 1A, 2025]', '2025-11-13 10:00:00', '2025-11-13 10:00:00', 128017);

-- Link user to courses (assuming user id is 1)
INSERT INTO `user_courses` (`user_id`, `course_id`) VALUES
(1, 127998),
(1, 128003),
(1, 127958),
(1, 128017);

-- Insert mock assignments
INSERT INTO `assignment` (`title`, `description`, `course_id`, `user_id`, `due_date`, `max_score`, `status`, `assignment_type`, `instructions`) VALUES
('Assignment 1: Data Mining Basics', 'Complete the basic data mining exercises', 127998, 1, '2025-11-20 23:59:59', 100.00, 'pending', 'homework', 'Submit via Moodle'),
('Project: Database Design', 'Design a database schema for a given scenario', 128003, 1, '2025-11-25 23:59:59', 150.00, 'pending', 'project', 'Include ER diagram and SQL scripts'),
('NLP Homework 1', 'Implement basic tokenization and stemming', 127958, 1, '2025-11-18 23:59:59', 80.00, 'completed', 'homework', 'Use Python NLTK library'),
('ML Quiz 1', 'Multiple choice questions on machine learning basics', 128017, 1, '2025-11-15 14:30:00', 50.00, 'completed', 'quiz', 'Online quiz on Moodle');

-- Insert mock study sessions
INSERT INTO `study_sessions` (`assignment_id`, `start_time`, `duration_minutes`, `notes`) VALUES
(1, '2025-11-13 09:00:00', 60, 'Studied data mining concepts'),
(2, '2025-11-13 14:00:00', 90, 'Worked on database design'),
(3, '2025-11-12 10:00:00', 45, 'Completed NLP homework'),
(4, '2025-11-11 16:00:00', 30, 'Reviewed ML quiz questions');
