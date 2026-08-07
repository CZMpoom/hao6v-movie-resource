-- 6v 影视资源库表结构
CREATE TABLE IF NOT EXISTS categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(64) NOT NULL COMMENT '类型名称',
  slug VARCHAR(64) NOT NULL UNIQUE COMMENT '类型标识',
  url VARCHAR(255) NOT NULL COMMENT '类型 URL',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='影视类型';

CREATE TABLE IF NOT EXISTS resources (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(500) NOT NULL COMMENT '列表页标题（来自 hao6v）',
  clean_title VARCHAR(500) DEFAULT NULL COMMENT '清洗后的标题',
  detail_url VARCHAR(500) NOT NULL UNIQUE COMMENT '站点详情页 URL（仅用于前端展示链接）',
  magnets TEXT COMMENT '磁力链接 JSON [{name,url}]（来自 hao6v）',
  media_type ENUM('movie','tv') DEFAULT NULL COMMENT '电影/剧集（来自 TMDB）',
  tmdb_id INT DEFAULT NULL COMMENT 'TMDB ID',
  tmdb_title VARCHAR(500) DEFAULT NULL COMMENT 'TMDB 标题',
  overview TEXT COMMENT '简介（来自 TMDB）',
  poster_path VARCHAR(255) DEFAULT NULL COMMENT 'TMDB 海报路径',
  release_date DATE DEFAULT NULL COMMENT '上映/首播日期（来自 TMDB）',
  year SMALLINT DEFAULT NULL COMMENT '年份（来自 TMDB）',
  rating DECIMAL(4,1) DEFAULT NULL COMMENT '评分（来自 TMDB vote_average）',
  episode_count INT DEFAULT NULL COMMENT '总集数（来自 TMDB）',
  director VARCHAR(500) DEFAULT NULL COMMENT '导演（来自 TMDB）',
  language VARCHAR(255) DEFAULT NULL COMMENT '语言（来自 TMDB）',
  country VARCHAR(255) DEFAULT NULL COMMENT '产地（来自 TMDB）',
  genre VARCHAR(255) DEFAULT NULL COMMENT '类型（来自 TMDB）',
  cast TEXT COMMENT '演员 JSON 数组（来自 TMDB）',
  tmdb_searched TINYINT NOT NULL DEFAULT 0 COMMENT '是否已执行过 TMDB 检索',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_year (year),
  KEY idx_tmdb (tmdb_id),
  KEY idx_media (media_type),
  KEY idx_tmdb_searched (tmdb_searched)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='影视资源';

CREATE TABLE IF NOT EXISTS resource_categories (
  resource_id INT NOT NULL,
  category_id INT NOT NULL,
  PRIMARY KEY (resource_id, category_id),
  KEY idx_category (category_id),
  CONSTRAINT fk_rc_resource FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
  CONSTRAINT fk_rc_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资源-类型关联';
