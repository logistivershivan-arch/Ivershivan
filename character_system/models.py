# 导入数据库工具
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# 创建数据库对象
db = SQLAlchemy()

# ==================== 基础表 ====================

# 用户表（登录注册用）
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)  # 用户ID，主键，自动增长
    username = db.Column(db.String(50), unique=True, nullable=False)  # 用户名，不能重复
    password = db.Column(db.String(100), nullable=False)  # 密码
    created_time = db.Column(db.DateTime, default=datetime.now)  # 创建时间

# 工程表（不同世界观工程，多开功能）
class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 工程名称
    description = db.Column(db.Text)  # 工程简介
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 属于哪个用户
    created_time = db.Column(db.DateTime, default=datetime.now)

# ==================== 角色相关表 ====================

# 角色表
class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10))
    birthday = db.Column(db.String(50))
    height = db.Column(db.String(20))
    weight = db.Column(db.String(20))
    description = db.Column(db.Text)
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'))  # 所属地区/国籍
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    created_time = db.Column(db.DateTime, default=datetime.now)
    # 关系
    region = db.relationship('Region', backref='characters')

    @property
    def avatar_path(self):
        """快速获取角色头像路径"""
        for img_rel in self.images:
            if img_rel.is_avatar:
                return img_rel.image.file_path
        return None  # 没设置头像返回None


# 角色自定义信息表（用户可以自己加额外属性）
class CharacterCustomField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'))
    field_name = db.Column(db.String(100))
    field_value = db.Column(db.Text)
    field_type = db.Column(db.String(10), default='short')  # short=短文本，long=长文本

# ==================== 图集相关表 ====================

# 图片表
class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 图片名称
    type = db.Column(db.String(50))  # 图片分类：立绘/背景/证件照/CG/插图
    file_path = db.Column(db.String(200), nullable=False)  # 文件保存路径
    description = db.Column(db.Text)  # 图片描述
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    created_time = db.Column(db.DateTime, default=datetime.now)


# 角色-图片关联表（一个角色可以有多张图，一张图可以对应多个角色）
class CharacterImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'))
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'))
    is_avatar = db.Column(db.Boolean, default=False)  # 是否是头像/主立绘

    character = db.relationship('Character', backref='images')
    image = db.relationship('Image', backref='characters')

# ==================== 阵营相关表 ====================

# 阵营表
class Faction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    parent_id = db.Column(db.Integer, db.ForeignKey('faction.id'))
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'))  # 所属地区
    created_time = db.Column(db.DateTime, default=datetime.now)

    # 关系
    children = db.relationship('Faction', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    region = db.relationship('Region', backref='factions')

# 角色-阵营关联表（一个角色可以属于多个阵营，每个阵营有不同职位）
class CharacterFaction(db.Model):
    __tablename__ = 'character_faction'
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'))
    faction_id = db.Column(db.Integer, db.ForeignKey('faction.id'))
    position = db.Column(db.String(100))  # 在该阵营的职位
    is_main = db.Column(db.Boolean, default=False)  # 是否是主阵营

    # 关系定义
    character = db.relationship('Character', backref='faction_relations')
    faction = db.relationship('Faction', backref='member_relations')
# ==================== 地区相关表 ====================

# 地区表
class Region(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    main_story = db.Column(db.Text)  # 地区主要故事
    parent_id = db.Column(db.Integer, db.ForeignKey('region.id'))  # 上级地区ID
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    created_time = db.Column(db.DateTime, default=datetime.now)

    # 子地区关系（支持无限层级：国家→省→市→区）
    children = db.relationship('Region', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')

# ==================== 故事线/章节相关表 ====================

# 长篇小说/多章节作品表
class Story(db.Model):
    __tablename__ = 'story'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100))
    description = db.Column(db.Text)
    cover_image_id = db.Column(db.Integer, db.ForeignKey('image.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    created_time = db.Column(db.DateTime, default=datetime.now)
    # 关系
    cover_image = db.relationship('Image')
    chapters = db.relationship('Chapter', backref='story', lazy='dynamic', order_by='Chapter.chapter_number')

# 故事/章节表
class Chapter(db.Model):
    __tablename__ = 'chapter'
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'))  # 所属长篇，空就是独立短篇
    chapter_number = db.Column(db.String(50))  # 章节号，比如"第一章"、"第3话"
    title = db.Column(db.String(200), nullable=False)  # 短篇标题/章节标题
    description = db.Column(db.Text)  # Summary/一句话简介
    content = db.Column(db.Text)  # 正文
    cover_image_id = db.Column(db.Integer, db.ForeignKey('image.id'))  # 短篇封面
    game_script_id = db.Column(db.Integer, db.ForeignKey('game_script.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    sort_order = db.Column(db.Integer, default=0)
    created_time = db.Column(db.DateTime, default=datetime.now)

    # 关系
    cover_image = db.relationship('Image')

# 故事-角色关联表（登场角色）
class ChapterCharacter(db.Model):
    __tablename__ = 'chapter_character'
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'))
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'))
    chapter = db.relationship('Chapter', backref='character_relations')
    character = db.relationship('Character', backref='chapters')

# 故事-地区关联表（发生地点，支持多个）
class ChapterRegion(db.Model):
    __tablename__ = 'chapter_region'
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'))
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'))
    chapter = db.relationship('Chapter', backref='region_relations')
    region = db.relationship('Region', backref='chapter_relations')

# 故事-阵营关联表（支持多个阵营、子阵营）
class ChapterFaction(db.Model):
    __tablename__ = 'chapter_faction'
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'))
    faction_id = db.Column(db.Integer, db.ForeignKey('faction.id'))
    chapter = db.relationship('Chapter', backref='faction_relations')
    faction = db.relationship('Faction', backref='chapters')
# ==================== 关系网相关表 ====================

# 角色关系表
class Relationship(db.Model):
    __tablename__ = 'relationship'
    id = db.Column(db.Integer, primary_key=True)
    character_a_id = db.Column(db.Integer, db.ForeignKey('character.id'))  # 角色A
    character_b_id = db.Column(db.Integer, db.ForeignKey('character.id'))  # 角色B
    relation_type = db.Column(db.String(50))  # 关系类型：朋友/敌人/师徒/亲人等
    description = db.Column(db.Text)  # 关系描述
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    created_time = db.Column(db.DateTime, default=datetime.now)

# ==================== 文字游戏相关表 ====================

# 游戏脚本表（一个完整的剧情游戏）
class GameScript(db.Model):
    __tablename__ = 'game_script'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # 脚本名称
    description = db.Column(db.Text)  # 脚本简介
    start_node_id = db.Column(db.Integer)  # 开始节点ID
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    created_time = db.Column(db.DateTime, default=datetime.now)

# 剧情节点表（每一句台词/每一个画面就是一个节点）
class GameNode(db.Model):
    __tablename__ = 'game_node'
    id = db.Column(db.Integer, primary_key=True)
    script_id = db.Column(db.Integer, db.ForeignKey('game_script.id'))  # 属于哪个脚本
    node_type = db.Column(db.String(20), default='dialogue')  # 节点类型：dialogue对话/choice分支/ending结局
    speaker = db.Column(db.String(100))  # 说话人
    text = db.Column(db.Text)  # 台词内容
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'))  # 关联角色（自动导入立绘）
    background_id = db.Column(db.Integer, db.ForeignKey('image.id'))  # 背景图ID
    cg_id = db.Column(db.Integer, db.ForeignKey('image.id'))  # CG图ID
    display_time = db.Column(db.Float, default=0)  # 自动播放时长（0表示点击继续）
    bgm_path = db.Column(db.String(500))  # BGM路径（可选，先留着）
    sort_order = db.Column(db.Integer, default=0)  # 排序
    is_key_node = db.Column(db.Boolean, default=False)  # 是否是关键节点
    created_time = db.Column(db.DateTime, default=datetime.now)

# 分支选项表
class GameChoice(db.Model):
    __tablename__ = 'game_choice'
    id = db.Column(db.Integer, primary_key=True)
    from_node_id = db.Column(db.Integer, db.ForeignKey('game_node.id'))  # 从哪个节点来
    to_node_id = db.Column(db.Integer, db.ForeignKey('game_node.id'))  # 跳到哪个节点
    choice_text = db.Column(db.String(500))  # 选项文字
    sort_order = db.Column(db.Integer, default=0)  # 选项排序


# 标签表
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 标签名称
    type = db.Column(db.String(50), nullable=False)  # 标签类型：character(角色)/faction(阵营)/region(地区)/custom(自定义)
    target_id = db.Column(db.Integer)  # 关联对应表的ID（自定义标签为空）
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    created_time = db.Column(db.DateTime, default=datetime.now)

    # 唯一约束：同类型同target的标签不重复
    __table_args__ = (db.UniqueConstraint('type', 'target_id', 'name', name='_tag_unique'),)


# 图片-标签关联表（多对多）
class ImageTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'))
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'))

    image = db.relationship('Image', backref='tag_relations')
    tag = db.relationship('Tag', backref='image_relations')