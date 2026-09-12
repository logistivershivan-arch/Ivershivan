from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from werkzeug.utils import secure_filename
import uuid
# 导入我们自己写的数据库模型
from models import db, User, Project, Character, Faction, Region, Story, Chapter, ChapterCharacter, ChapterRegion, ChapterFaction, Image, Relationship, CharacterCustomField, CharacterFaction, CharacterImage, Tag, ImageTag
from models import db, User, Project, Character, Faction, Region, Chapter, ChapterCharacter, ChapterRegion, ChapterFaction, Image, Relationship, CharacterCustomField, CharacterFaction, CharacterImage, Tag, ImageTag
from models import db, User, Project, Character, Faction, Region, Chapter, ChapterCharacter, ChapterRegion, Image, Relationship, CharacterCustomField, CharacterFaction, CharacterImage, Tag, ImageTag
from models import db, User, Project, Character, Faction, Region, Chapter, Image, Relationship, CharacterCustomField, CharacterFaction
from models import db, User, Project, Character, Faction, Region, Chapter, Image, Relationship, CharacterCustomField, CharacterFaction, CharacterImage, Tag, ImageTag
# 创建Flask应用
app = Flask(__name__)

# ==================== 配置项 ====================
# 数据库配置：切换为MySQL（交作业用），把root:后面的「你的MySQL密码」改成你安装MySQL时设置的root密码
# 使用前先在MySQL里手动新建一个名为 character_system 的空数据库（不用建表，程序启动会自动创建）
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:louruiqin0808@localhost/character_system?charset=utf8mb4'
# 之后想切回SQLite，把上面注释掉，取消下面这行的注释就行
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///character_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# 会话密钥（登录功能需要）
app.config['SECRET_KEY'] = 'your_secret_key_here'
# 图片上传文件夹
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'images')
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 支持最大32MB图片上传

# 初始化数据库
db.init_app(app)

# 初始化登录管理
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# 加载用户的回调函数
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 全局拦截：没选世界观就跳选择页（排除登录、世界观相关页面）
@app.before_request
def check_project():
    # 不需要选世界观的页面
    no_need_project = ['login', 'project_list', 'project_new', 'project_edit', 'project_switch', 'static']
    if request.endpoint in no_need_project:
        return None
    # 没选世界观就跳选择页
    if 'current_project_id' not in session:
        return redirect(url_for('project_list'))
    return None

# ==================== 确保文件夹存在 ====================
with app.app_context():
    # 创建所有数据表
    db.create_all()
    # 确保图片上传文件夹存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # 创建默认测试用户（如果不存在）
    if not User.query.filter_by(username='admin').first():
        test_user = User(username='admin', password='123456')
        db.session.add(test_user)
        db.session.commit()
        print("默认用户创建成功：用户名 admin，密码 123456")


# ==================== 首页 ====================
@app.route('/')
@login_required
def index():
    return render_template('index.html')


# 登录页面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        flash('用户名或密码错误', 'error')
    return render_template('login.html')


# 登出
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# 世界观列表页
@app.route('/projects')
@login_required
def project_list():
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.created_time.desc()).all()
    return render_template('project_list.html', projects=projects, hide_sidebar=True)

# 新建世界观
@app.route('/project/new', methods=['GET', 'POST'])
@login_required
def project_new():
    if request.method == 'POST':
        project = Project(
            name=request.form.get('name'),
            description=request.form.get('description'),
            user_id=current_user.id
        )
        db.session.add(project)
        db.session.commit()
        flash('世界观创建成功', 'success')
        return redirect(url_for('project_list'))
    return render_template('project_form.html', project=None, hide_sidebar=True)

# 切换世界观
@app.route('/project/switch/<int:project_id>')
@login_required
def project_switch(project_id):
    project = Project.query.get_or_404(project_id)
    session['current_project_id'] = project.id
    session['current_project_name'] = project.name
    return redirect(url_for('index'))

# 编辑世界观
@app.route('/project/edit/<int:project_id>', methods=['GET', 'POST'])
@login_required
def project_edit(project_id):
    project = Project.query.get_or_404(project_id)
    if request.method == 'POST':
        project.name = request.form.get('name')
        project.description = request.form.get('description')
        db.session.commit()
        # 如果改的是当前选中的世界观，更新session
        if session.get('current_project_id') == project.id:
            session['current_project_name'] = project.name
        flash('修改成功', 'success')
        return redirect(url_for('project_list'))
    return render_template('project_form.html', project=project, hide_sidebar=True)

# ==================== 角色管理模块 ====================

# 角色列表页
@app.route('/characters')
@login_required
def character_list():
    current_pid = session.get('current_project_id', 1)
    # 获取搜索参数
    keyword = request.args.get('keyword', '')
    faction_id = request.args.get('faction_id', type=int)

    # 基础查询（加世界观过滤）
    query = Character.query.filter_by(project_id=current_pid)

    # 按名字搜索
    if keyword:
        query = query.filter(Character.name.like(f'%{keyword}%'))

    # 按阵营筛选（通过中间表关联查询）
    if faction_id:
        query = query.join(CharacterFaction).filter(CharacterFaction.faction_id == faction_id)

    characters = query.all()

    # 获取所有阵营，用于筛选下拉框（加世界观过滤）
    factions = Faction.query.filter_by(project_id=current_pid, parent_id=None).all()

    return render_template('character_list.html',
                         characters=characters,
                         factions=factions,
                         keyword=keyword,
                         selected_faction=faction_id)

# 新增角色
@app.route('/character/new', methods=['GET', 'POST'])
@login_required
def character_new():
    current_pid = session.get('current_project_id', 1)
    if request.method == 'POST':
        # 从表单获取数据
        character = Character(
            name=request.form.get('name'),
            gender=request.form.get('gender'),
            birthday=request.form.get('birthday'),
            height=request.form.get('height'),
            weight=request.form.get('weight'),
            description=request.form.get('description'),
            region_id=request.form.get('region_id', type=int),  # 加这行
            project_id=current_pid
        )
        db.session.add(character)
        db.session.flush()  # 先获取新角色的ID
        # 保存主阵营
        main_faction_id = request.form.get('main_faction_id', type=int)
        main_position = request.form.get('main_position', '')
        if main_faction_id:
            main_rel = CharacterFaction(
                character_id=character.id,
                faction_id=main_faction_id,
                position=main_position,
                is_main=True
            )
            db.session.add(main_rel)

        # 保存副阵营
        sub_faction_ids = request.form.getlist('sub_faction_id[]')
        sub_positions = request.form.getlist('sub_position[]')
        for fid, pos in zip(sub_faction_ids, sub_positions):
            if fid:
                sub_rel = CharacterFaction(
                    character_id=character.id,
                    faction_id=int(fid),
                    position=pos,
                    is_main=False
                )
                db.session.add(sub_rel)

        # 重新保存自定义字段
        custom_names = request.form.getlist('custom_name[]')
        custom_values = request.form.getlist('custom_value[]')
        custom_types = request.form.getlist('custom_type[]')
        for name, value, ftype in zip(custom_names, custom_values, custom_types):
            if name.strip():
                custom_field = CharacterCustomField(
                    character_id=character.id,
                    field_name=name.strip(),
                    field_value=value.strip(),
                    field_type=ftype if ftype else 'short'
                )
                db.session.add(custom_field)
        db.session.commit()
        flash('角色创建成功！', 'success')
        return redirect(url_for('character_list'))

    factions = Faction.query.filter_by(project_id=current_pid).all()
    custom_fields = []  # 新增角色时自定义字段是空的
    main_faction = None
    main_position = ''
    sub_factions = []
    regions = Region.query.filter_by(project_id=current_pid, parent_id=None).all()  # 查所有顶级国家
    all_regions = get_all_regions()  # 所有地区（含子地区）
    return render_template('character_form.html',
                           character=None,
                           factions=factions,
                           custom_fields=custom_fields,
                           main_faction=main_faction,
                           main_position=main_position,
                           sub_factions=sub_factions,
                           all_regions=all_regions,
                           selected_region=None)


# 编辑角色
@app.route('/character/<int:character_id>/edit', methods=['GET', 'POST'])
@login_required
def character_edit(character_id):
    current_pid = session.get('current_project_id', 1)
    character = Character.query.get_or_404(character_id)

    if request.method == 'POST':
        # 更新基本信息
        character.name = request.form.get('name')
        character.gender = request.form.get('gender')
        character.birthday = request.form.get('birthday')
        character.height = request.form.get('height')
        character.weight = request.form.get('weight')
        character.description = request.form.get('description')
        character.region_id = request.form.get('region_id', type=int)

        # ===== 关键：先删掉旧的阵营关系，再加新的 =====
        CharacterFaction.query.filter_by(character_id=character.id).delete()

        # 保存主阵营
        main_faction_id = request.form.get('main_faction_id', type=int)
        main_position = request.form.get('main_position', '')
        if main_faction_id:
            main_rel = CharacterFaction(
                character_id=character.id,
                faction_id=main_faction_id,
                position=main_position,
                is_main=True
            )
            db.session.add(main_rel)

        # 保存副阵营
        sub_faction_ids = request.form.getlist('sub_faction_id[]')
        sub_positions = request.form.getlist('sub_position[]')
        for fid, pos in zip(sub_faction_ids, sub_positions):
            if fid:
                sub_rel = CharacterFaction(
                    character_id=character.id,
                    faction_id=int(fid),
                    position=pos,
                    is_main=False
                )
                db.session.add(sub_rel)

        # ===== 关键：先删掉旧的自定义字段，再加新的 =====
        CharacterCustomField.query.filter_by(character_id=character.id).delete()

        # 保存自定义字段
        custom_names = request.form.getlist('custom_name[]')
        custom_values = request.form.getlist('custom_value[]')
        custom_types = request.form.getlist('custom_type[]')
        for name, value, ftype in zip(custom_names, custom_values, custom_types):
            if name.strip():  # 名字不为空才保存
                custom_field = CharacterCustomField(
                    character_id=character.id,
                    field_name=name.strip(),
                    field_value=value.strip(),
                    field_type=ftype if ftype else 'short'
                )
                db.session.add(custom_field)

        db.session.commit()
        flash('角色更新成功！', 'success')
        return redirect(url_for('character_list'))

    # GET请求：查询已有数据回显
    factions = Faction.query.filter_by(project_id=current_pid).all()
    regions = Region.query.filter_by(project_id=current_pid, parent_id=None).all()
    # 查询自定义字段
    custom_fields = CharacterCustomField.query.filter_by(character_id=character_id).all()
    # 查询主副阵营
    main_faction = None
    main_position = ''
    sub_factions = []
    for rel in character.faction_relations:
        if rel.is_main:
            main_faction = rel.faction
            main_position = rel.position
        else:
            sub_factions.append((rel.faction, rel.position))

    all_regions = get_all_regions()
    selected_region = character.region_id
    return render_template('character_form.html',
                           character=character,
                           factions=factions,
                           custom_fields=custom_fields,
                           main_faction=main_faction,
                           main_position=main_position,
                           sub_factions=sub_factions,
                           all_regions=all_regions,
                           selected_region=selected_region)

# 角色详情页
@app.route('/character/<int:character_id>')
@login_required
def character_detail(character_id):
    character = Character.query.get_or_404(character_id)

    # 查主阵营和副阵营
    main_faction = None
    main_position = ''
    sub_factions = []
    for rel in character.faction_relations:
        if rel.is_main:
            main_faction = rel.faction
            main_position = rel.position
        else:
            sub_factions.append((rel.faction, rel.position))

    # 同阵营成员（主阵营的成员）
    faction_members = []
    if main_faction:
        faction_members = [rel.character for rel in main_faction.member_relations if rel.character.id != character.id]

    # 查询自定义字段
    custom_fields = CharacterCustomField.query.filter_by(character_id=character_id).all()

    return render_template('character_detail.html',
                           character=character,
                           main_faction=main_faction,
                           main_position=main_position,
                           sub_factions=sub_factions,
                           faction_members=faction_members,
                           custom_fields=custom_fields,
                           region=character.region)  # 加这行


# 删除角色
@app.route('/character/<int:character_id>/delete')
@login_required
def character_delete(character_id):
    character = Character.query.get_or_404(character_id)
    db.session.delete(character)
    db.session.commit()
    flash('角色删除成功！', 'success')
    return redirect(url_for('character_list'))


# ==================== 阵营管理模块 ====================

# 阵营列表页
@app.route('/factions')
@login_required
def faction_list():
    current_pid = session.get('current_project_id', 1)
    # 只查顶级阵营，子阵营在页面里展开
    factions = Faction.query.filter_by(project_id=current_pid, parent_id=None).all()
    return render_template('faction_list.html', factions=factions)

# 新增阵营
@app.route('/faction/new', methods=['GET', 'POST'])
@login_required
def faction_new():
    current_pid = session.get('current_project_id', 1)
    # 获取url传过来的默认上级阵营id
    default_parent_id = request.args.get('parent_id', type=int)

    if request.method == 'POST':
        faction = Faction(
            name=request.form.get('name'),
            description=request.form.get('description'),
            parent_id=request.form.get('parent_id', type=int),
            region_id=request.form.get('region_id', type=int),
            project_id=current_pid
        )
        db.session.add(faction)
        db.session.commit()
        flash('阵营创建成功！', 'success')
        return redirect(url_for('faction_list'))

    all_factions = Faction.query.filter_by(project_id=current_pid, parent_id=None).all()
    all_regions = get_all_regions()
    return render_template('faction_form.html',
                           faction=None,
                           all_factions=all_factions,
                           default_parent_id=default_parent_id,
                           all_regions=all_regions,
                           selected_region=None)


# 编辑阵营
@app.route('/faction/<int:faction_id>/edit', methods=['GET', 'POST'])
@login_required
def faction_edit(faction_id):
    current_pid = session.get('current_project_id', 1)
    faction = Faction.query.get_or_404(faction_id)

    if request.method == 'POST':
        faction.name = request.form.get('name')
        faction.description = request.form.get('description')
        faction.parent_id = request.form.get('parent_id', type=int)
        faction.region_id = request.form.get('region_id', type=int)
        db.session.commit()
        flash('阵营更新成功！', 'success')
        return redirect(url_for('faction_list'))

    all_factions = Faction.query.filter_by(project_id=current_pid, parent_id=None).all()
    all_regions = get_all_regions()
    selected_region = faction.region_id
    return render_template('faction_form.html',
                           faction=faction,
                           all_factions=all_factions,
                           all_regions=all_regions,
                           selected_region=selected_region,
                           default_parent_id=None)

# 阵营详情页
@app.route('/faction/<int:faction_id>')
@login_required
def faction_detail(faction_id):
    faction = Faction.query.get_or_404(faction_id)
    # 查该阵营的所有成员和对应的职位
    members = []
    for rel in faction.member_relations:
        members.append((rel.character, rel.position, rel.is_main))
    return render_template('faction_detail.html', faction=faction, members=members)


# 删除阵营
@app.route('/faction/<int:faction_id>/delete')
@login_required
def faction_delete(faction_id):
    faction = Faction.query.get_or_404(faction_id)
    db.session.delete(faction)
    db.session.commit()
    flash('阵营删除成功！', 'success')
    return redirect(url_for('faction_list'))

# ==================== 地区管理 ====================
# 地区列表
@app.route('/regions')
@login_required
def region_list():
    current_pid = session.get('current_project_id', 1)
    # 只查顶级地区（国家），子地区在页面折叠
    regions = Region.query.filter_by(project_id=current_pid, parent_id=None).all()
    return render_template('region_list.html', regions=regions)


# 新增地区
@app.route('/region/new', methods=['GET', 'POST'])
@login_required
def region_new():
    current_pid = session.get('current_project_id', 1)
    default_parent_id = request.args.get('parent_id', type=int)
    if request.method == 'POST':
        region = Region(
            name=request.form.get('name'),
            description=request.form.get('description'),
            main_story=request.form.get('main_story'),
            parent_id=request.form.get('parent_id', type=int),
            project_id=current_pid
        )
        db.session.add(region)
        db.session.commit()
        flash('地区创建成功！', 'success')
        return redirect(url_for('region_list'))

    # 查所有顶级地区作为上级选项
    all_regions = Region.query.filter_by(project_id=current_pid, parent_id=None).all()
    return render_template('region_form.html', region=None, all_regions=all_regions, default_parent_id=default_parent_id)


# 编辑地区
@app.route('/region/<int:region_id>/edit', methods=['GET', 'POST'])
@login_required
def region_edit(region_id):
    current_pid = session.get('current_project_id', 1)
    region = Region.query.get_or_404(region_id)
    if request.method == 'POST':
        region.name = request.form.get('name')
        region.description = request.form.get('description')
        region.main_story = request.form.get('main_story')
        region.parent_id = request.form.get('parent_id', type=int)
        db.session.commit()
        flash('地区更新成功！', 'success')
        return redirect(url_for('region_list'))

    all_regions = Region.query.filter_by(project_id=current_pid, parent_id=None).all()
    return render_template('region_form.html', region=region, all_regions=all_regions, default_parent_id=None)


# 地区详情
@app.route('/region/<int:region_id>')
@login_required
def region_detail(region_id):
    current_pid = session.get('current_project_id', 1)
    region = Region.query.get_or_404(region_id)
    # 查地区标签和关联图片
    region_tag = Tag.query.filter_by(type='region', target_id=region_id, project_id=current_pid).first()
    region_images = []
    local_factions = []
    local_characters = []
    if region_tag:
        # 最新的图片在前，最多取8张
        region_images = sorted([rel.image for rel in region_tag.image_relations],
                              key=lambda x: x.created_time, reverse=True)[:8]
    # 查本地阵营（所属地区是当前地区的阵营，后面做，先留空）
    # 查本地角色（国籍是当前地区的角色）
    local_characters = Character.query.filter_by(region_id=region_id, project_id=current_pid).all()
    return render_template('region_detail.html',
                         region=region,
                         region_tag=region_tag,
                         region_images=region_images,
                         local_factions=local_factions,
                         local_characters=local_characters)

# 删除地区
@app.route('/region/<int:region_id>/delete')
@login_required
def region_delete(region_id):
    region = Region.query.get_or_404(region_id)
    db.session.delete(region)
    db.session.commit()
    flash('地区删除成功！', 'success')
    return redirect(url_for('region_list'))


# ==================== 图集管理 ====================
# 允许的图片格式
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def get_all_regions(parent_id=None, level=0):
    current_pid = session.get('current_project_id', 1)
    regions = []
    items = Region.query.filter_by(project_id=current_pid, parent_id=parent_id).order_by(Region.id).all()
    for r in items:
        prefix = "　└ " if level > 0 else ""
        regions.append((r.id, prefix + r.name))
        regions.extend(get_all_regions(r.id, level+1))
    return regions

# 递归获取所有阵营（带缩进，用于下拉选择）
def get_all_factions(parent_id=None, level=0):
    current_pid = session.get('current_project_id', 1)
    factions = []
    items = Faction.query.filter_by(project_id=current_pid, parent_id=parent_id).order_by(Faction.id).all()
    for f in items:
        prefix = "　└ " if level > 0 else ""
        factions.append((f.id, prefix + f.name))
        factions.extend(get_all_factions(f.id, level+1))
    return factions

# 工具函数：按父级分组地区/阵营，生成"父-子1、子2 父2-子3"格式
def group_hierarchy(items):
    if not items:
        return ""
    # 分顶级和子级
    parents = [i for i in items if not i.parent_id]
    children = [i for i in items if i.parent_id]
    result = []
    for p in parents:
        # 找当前父级的子级
        childs = [c for c in children if c.parent_id == p.id]
        if childs:
            child_names = "、".join([c.name for c in childs])
            result.append(f"{p.name}-{child_names}")
        else:
            result.append(p.name)
    return " ".join(result)

# 图片列表
@app.route('/images')
@login_required
def image_list():
    current_pid = session.get('current_project_id', 1)
    image_type = request.args.get('type', '')
    tag_id = request.args.get('tag_id', type=int)
    query = Image.query.filter_by(project_id=current_pid)

    if image_type:
        query = query.filter_by(type=image_type)
    if tag_id:
        query = query.join(ImageTag).filter(ImageTag.tag_id == tag_id)

    images = query.order_by(Image.created_time.desc()).all()

    # 给每个图片查标签
    image_tags = {}
    for img in images:
        tags = [rel.tag for rel in img.tag_relations]
        image_tags[img.id] = tags

    return render_template('image_list.html',
                           images=images,
                           current_type=image_type,
                           image_tags=image_tags,
                           current_tag=Tag.query.get(tag_id) if tag_id else None)


# 上传图片
@app.route('/image/upload', methods=['GET', 'POST'])
@login_required
def image_upload():
    current_pid = session.get('current_project_id', 1)
    if request.method == 'POST':
        file = request.files.get('image_file')
        if not file or file.filename == '':
            flash('请选择要上传的图片', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # 生成唯一文件名，防止重名
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            # 保存图片基本信息
            image = Image(
                name=filename,
                type=request.form.get('type'),
                file_path=f'images/{filename}',
                description=request.form.get('description'),
                project_id=current_pid
            )
            db.session.add(image)
            db.session.flush()  # 获取图片ID

            # ===== 处理标签 =====
            # 1. 角色标签（多选）
            character_ids = request.form.getlist('character_tags[]')
            for cid in character_ids:
                if cid:
                    cid = int(cid)
                    char = Character.query.get(cid)
                    if char:
                        # 查找或创建标签
                        tag = Tag.query.filter_by(type='character', target_id=cid, project_id=current_pid).first()
                        if not tag:
                            tag = Tag(name=char.name, type='character', target_id=cid, project_id=current_pid)
                            db.session.add(tag)
                            db.session.flush()
                        # 关联图片和标签
                        img_tag = ImageTag(image_id=image.id, tag_id=tag.id)
                        db.session.add(img_tag)
                        # 关联角色和图片（用于头像、角色图集）
                        char_img = CharacterImage(character_id=cid, image_id=image.id, is_avatar=False)
                        db.session.add(char_img)

            # 2. 阵营标签（单选）
            faction_id = request.form.get('faction_tag', type=int)
            if faction_id:
                faction = Faction.query.get(faction_id)
                if faction:
                    tag = Tag.query.filter_by(type='faction', target_id=faction_id, project_id=current_pid).first()
                    if not tag:
                        tag = Tag(name=faction.name, type='faction', target_id=faction_id, project_id=current_pid)
                        db.session.add(tag)
                        db.session.flush()
                    img_tag = ImageTag(image_id=image.id, tag_id=tag.id)
                    db.session.add(img_tag)

            # 3. 地区标签（多选）
            region_ids = request.form.getlist('region_tags')
            for rid in region_ids:
                if rid and rid.strip():
                    rid = int(rid)
                    region = Region.query.get(rid)
                    if region:
                        tag = Tag.query.filter_by(type='region', target_id=rid, project_id=current_pid).first()
                        if not tag:
                            tag = Tag(name=region.name, type='region', target_id=rid, project_id=current_pid)
                            db.session.add(tag)
                            db.session.flush()
                        img_tag = ImageTag(image_id=image.id, tag_id=tag.id)
                        db.session.add(img_tag)

            # 4. 自定义标签
            custom_tags = request.form.getlist('custom_tags[]')
            for tag_name in custom_tags:
                tag_name = tag_name.strip()
                if tag_name:
                    tag = Tag.query.filter_by(type='custom', name=tag_name, project_id=current_pid).first()
                    if not tag:
                        tag = Tag(name=tag_name, type='custom', project_id=current_pid)
                        db.session.add(tag)
                        db.session.flush()
                    img_tag = ImageTag(image_id=image.id, tag_id=tag.id)
                    db.session.add(img_tag)

            db.session.commit()
            flash('图片上传成功！', 'success')
            return redirect(url_for('image_list'))
        else:
            flash('不支持的图片格式，仅支持png/jpg/jpeg/gif/webp', 'error')
            return redirect(request.url)

    # GET请求：传所有角色、阵营、地区给表单选标签
    characters = Character.query.filter_by(project_id=current_pid).all()
    factions = Faction.query.filter_by(project_id=current_pid, parent_id=None).all()
    all_regions = get_all_regions()
    return render_template('image_form.html',
                           characters=characters,
                           factions=factions,
                           all_regions=all_regions,
                           selected_characters=[],
                           selected_faction=None,
                           selected_regions=[],
                           custom_tags=[],
                           image=None)

    # 图片详情
@app.route('/image/<int:image_id>')
@login_required
def image_detail(image_id):
        image = Image.query.get_or_404(image_id)
        # 提前查好这张图关联的角色，避免模板里直接访问模型
        image_characters = []
        other_tags = []
        for rel in image.tag_relations:
            tag = rel.tag
            if tag.type == 'character':
                char = Character.query.get(tag.target_id)
                if char:
                    is_avatar = (char.avatar_path == image.file_path)
                    image_characters.append((char, tag, is_avatar))
            else:
                other_tags.append(tag)
        return render_template('image_detail.html',
                               image=image,
                               image_characters=image_characters,
                               other_tags=other_tags)

    # 编辑图片
@app.route('/image/<int:image_id>/edit', methods=['GET', 'POST'])
@login_required
def image_edit(image_id):
        current_pid = session.get('current_project_id', 1)
        image = Image.query.get_or_404(image_id)

        if request.method == 'POST':
            # 更新基本信息
            image.name = request.form.get('name') or image.name
            image.type = request.form.get('type')
            image.description = request.form.get('description')

            # 先删掉所有旧标签关联和角色图片关联，再加新的
            ImageTag.query.filter_by(image_id=image.id).delete()
            CharacterImage.query.filter_by(image_id=image.id).delete()

            # 1. 角色标签（多选）
            character_ids = request.form.getlist('character_tags[]')
            for cid in character_ids:
                if cid:
                    cid = int(cid)
                    char = Character.query.get(cid)
                    if char:
                        tag = Tag.query.filter_by(type='character', target_id=cid, project_id=current_pid).first()
                        if not tag:
                            tag = Tag(name=char.name, type='character', target_id=cid, project_id=current_pid)
                            db.session.add(tag)
                            db.session.flush()
                        img_tag = ImageTag(image_id=image.id, tag_id=tag.id)
                        db.session.add(img_tag)
                        char_img = CharacterImage(character_id=cid, image_id=image.id, is_avatar=False)
                        db.session.add(char_img)

            # 2. 阵营标签
            faction_id = request.form.get('faction_tag', type=int)
            if faction_id:
                faction = Faction.query.get(faction_id)
                if faction:
                    tag = Tag.query.filter_by(type='faction', target_id=faction_id, project_id=current_pid).first()
                    if not tag:
                        tag = Tag(name=faction.name, type='faction', target_id=faction_id, project_id=current_pid)
                        db.session.add(tag)
                        db.session.flush()
                    img_tag = ImageTag(image_id=image.id, tag_id=tag.id)
                    db.session.add(img_tag)

            # 3. 地区标签（多选）
            region_ids = request.form.getlist('region_tags')
            for rid in region_ids:
                if rid and rid.strip():
                    rid = int(rid)
                    region = Region.query.get(rid)
                    if region:
                        tag = Tag.query.filter_by(type='region', target_id=rid, project_id=current_pid).first()
                        if not tag:
                            tag = Tag(name=region.name, type='region', target_id=rid, project_id=current_pid)
                            db.session.add(tag)
                            db.session.flush()
                        img_tag = ImageTag(image_id=image.id, tag_id=tag.id)
                        db.session.add(img_tag)

            # 4. 自定义标签
            custom_tags = request.form.getlist('custom_tags[]')
            for tag_name in custom_tags:
                tag_name = tag_name.strip()
                if tag_name:
                    tag = Tag.query.filter_by(type='custom', name=tag_name, project_id=current_pid).first()
                    if not tag:
                        tag = Tag(name=tag_name, type='custom', project_id=current_pid)
                        db.session.add(tag)
                        db.session.flush()
                    img_tag = ImageTag(image_id=image.id, tag_id=tag.id)
                    db.session.add(img_tag)

            db.session.commit()
            flash('图片信息更新成功！', 'success')
            return redirect(url_for('image_detail', image_id=image.id))

        # GET请求：回显已有数据
        characters = Character.query.filter_by(project_id=current_pid).all()
        factions = Faction.query.filter_by(project_id=current_pid, parent_id=None).all()
        all_regions = get_all_regions()

        # 查已有的标签
        selected_characters = []
        selected_faction = None
        selected_regions = []
        custom_tags = []
        for rel in image.tag_relations:
            tag = rel.tag
            if tag.type == 'character':
                selected_characters.append(tag.target_id)
            elif tag.type == 'faction':
                selected_faction = tag.target_id
            elif tag.type == 'region':
                selected_regions.append(tag.target_id)
            elif tag.type == 'custom':
                custom_tags.append(tag.name)

        return render_template('image_form.html',
                               image=image,
                               characters=characters,
                               factions=factions,
                               all_regions=all_regions,
                               selected_characters=selected_characters,
                               selected_faction=selected_faction,
                               selected_regions=selected_regions,
                               custom_tags=custom_tags)

    # 设置角色头像
@app.route('/image/<int:image_id>/set-avatar/<int:character_id>')
@login_required
def set_avatar(image_id, character_id):
        image = Image.query.get_or_404(image_id)
        character = Character.query.get_or_404(character_id)

        # 查找或创建角色-图片关联（没有就自动建，兼容旧图）
        has_rel = CharacterImage.query.filter_by(image_id=image_id, character_id=character_id).first()
        if not has_rel:
            has_rel = CharacterImage(character_id=character_id, image_id=image_id, is_avatar=False)
            db.session.add(has_rel)
            db.session.flush()

        # 先取消该角色原来的所有头像（保证只有一个）
        CharacterImage.query.filter_by(character_id=character_id, is_avatar=True).update({'is_avatar': False})
        # 把当前图设为新头像
        has_rel.is_avatar = True
        db.session.commit()

        flash(f'已将{character.name}的头像设置为这张图', 'success')
        return redirect(url_for('image_detail', image_id=image_id))

    # 删除图片
@app.route('/image/<int:image_id>/delete')
@login_required
def image_delete(image_id):
        image = Image.query.get_or_404(image_id)
        # 删除服务器上的文件
        file_path = os.path.join(app.root_path, 'static', image.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        # 删除数据库记录
        db.session.delete(image)
        db.session.commit()
        flash('图片删除成功！', 'success')
        return redirect(url_for('image_list'))

    # ==================== 故事管理 ====================
    # 选择新建类型（短篇/长篇）
@app.route('/story/new/choose')
@login_required
def story_new_choose():
        return render_template('story_new_choose.html')

    # 新建长篇基本信息
@app.route('/story/new/long', methods=['GET', 'POST'])
@login_required
def story_new_long():
        current_pid = session.get('current_project_id', 1)
        if request.method == 'POST':
            story = Story(
                title=request.form.get('title'),
                author=request.form.get('author'),
                description=request.form.get('description'),
                project_id=current_pid
            )
            db.session.add(story)
            db.session.commit()
            flash('长篇创建成功，现在可以添加章节了', 'success')
            return redirect(url_for('story_long_detail', story_id=story.id))  # 这里修正了跳转地址，之前写错了
        return render_template('story_long_form.html', story=None)

    # 长篇详情页（章节目录）
@app.route('/story/long/<int:story_id>')
@login_required
def story_long_detail(story_id):
        story = Story.query.get_or_404(story_id)
        # 计算总字数
        total_words = sum([len(ch.content) if ch.content else 0 for ch in story.chapters])
        return render_template('story_long_detail.html', story=story, total_words=total_words)

    # 给长篇新建章节
@app.route('/story/long/<int:story_id>/chapter/new', methods=['GET', 'POST'])
@login_required
def chapter_new(story_id):
        current_pid = session.get('current_project_id', 1)
        story = Story.query.get_or_404(story_id)
        if request.method == 'POST':
            chapter = Chapter(
                story_id=story.id,
                chapter_number=request.form.get('chapter_number'),
                title=request.form.get('title'),
                description=request.form.get('description'),
                content=request.form.get('content'),
                project_id=current_pid
            )
            db.session.add(chapter)
            db.session.flush()

            # 保存关联标签（和短篇一样）
            character_ids = request.form.getlist('character_ids[]')
            for cid in character_ids:
                if cid:
                    cc = ChapterCharacter(chapter_id=chapter.id, character_id=int(cid))
                    db.session.add(cc)
            region_ids = request.form.getlist('region_ids[]')
            for rid in region_ids:
                if rid:
                    cr = ChapterRegion(chapter_id=chapter.id, region_id=int(rid))
                    db.session.add(cr)
            faction_ids = request.form.getlist('faction_ids[]')
            for fid in faction_ids:
                if fid:
                    cf = ChapterFaction(chapter_id=chapter.id, faction_id=int(fid))
                    db.session.add(cf)

            db.session.commit()
            flash('章节添加成功', 'success')
            return redirect(url_for('story_long_detail', story_id=story.id))

        characters = Character.query.filter_by(project_id=current_pid).all()
        all_factions = get_all_factions()
        all_regions = get_all_regions()
        return render_template('chapter_form.html',
                               story=story,
                               chapter=None,
                               characters=characters,
                               all_factions=all_factions,
                               all_regions=all_regions,
                               selected_characters=[],
                               selected_factions=[],
                               selected_regions=[])

    # 故事列表
@app.route('/stories')
@login_required
def story_list():
        current_pid = session.get('current_project_id', 1)
        # 查所有短篇（story_id为空）和所有长篇（加世界观过滤）
        short_stories = Chapter.query.filter_by(project_id=current_pid, story_id=None).order_by(
            Chapter.created_time.desc()).all()
        long_stories = Story.query.filter_by(project_id=current_pid).order_by(Story.created_time.desc()).all()

        # 处理短篇的链接
        for story in short_stories:
            story.is_long = False
            story.view_url = url_for('story_detail', chapter_id=story.id)
            story.edit_url = url_for('story_edit', story_id=story.id)
            # 短篇字数
            story.word_count = len(story.content) if story.content else 0
            # 拼地区阵营链接（和之前一样）
            regions = [rel.region for rel in story.region_relations]
            parent_regions = [r for r in regions if not r.parent_id]
            regions_parts = []
            for p in parent_regions:
                child_regions = [r for r in regions if r.parent_id == p.id]
                part = f'<a href="{url_for("region_detail", region_id=p.id)}" style="color: #1890ff; text-decoration: none; display:inline; white-space:nowrap;">{p.name}</a>'
                if child_regions:
                    child_links = []
                    for c in child_regions:
                        child_links.append(
                            f'<a href="{url_for("region_detail", region_id=c.id)}" style="color: #1890ff; text-decoration: none; display:inline; white-space:nowrap;">{c.name}</a>')
                    part += '-' + '、'.join(child_links)
                regions_parts.append(part)
            story.regions_html = '&nbsp;&nbsp;'.join(regions_parts)

            factions = [rel.faction for rel in story.faction_relations]
            parent_factions = [f for f in factions if not f.parent_id]
            factions_parts = []
            for p in parent_factions:
                child_factions = [f for f in factions if f.parent_id == p.id]
                part = f'<a href="{url_for("faction_detail", faction_id=p.id)}" style="color: #1890ff; text-decoration: none; display:inline; white-space:nowrap;">{p.name}</a>'
                if child_factions:
                    child_links = []
                    for c in child_factions:
                        child_links.append(
                            f'<a href="{url_for("faction_detail", faction_id=c.id)}" style="color: #1890ff; text-decoration: none; display:inline; white-space:nowrap;">{c.name}</a>')
                    part += '-' + '、'.join(child_links)
                factions_parts.append(part)
            story.factions_html = '&nbsp;&nbsp;'.join(factions_parts)
            story.char_list = [rel.character for rel in story.character_relations]

        # 处理长篇
        for story in long_stories:
            story.is_long = True
            story.view_url = url_for('story_long_detail', story_id=story.id)
            story.edit_url = '#'  # 改这行，先占位，等后面做长篇编辑功能再改
            # 长篇总字数
            story.word_count = sum([len(ch.content) if ch.content else 0 for ch in story.chapters])
            story.regions_html = ''
            story.factions_html = ''
            story.char_list = []

        # 合并按时间排序
        all_items = short_stories + long_stories
        all_items.sort(key=lambda x: x.created_time, reverse=True)
        return render_template('story_list.html', stories=all_items)

    # 新增故事
@app.route('/story/new', methods=['GET', 'POST'])
@login_required
def story_new():
        current_pid = session.get('current_project_id', 1)
        if request.method == 'POST':
            story = Chapter(
                title=request.form.get('title'),
                description=request.form.get('description'),
                content=request.form.get('content'),
                project_id=current_pid
            )
            db.session.add(story)
            db.session.flush()

            # 保存登场角色
            character_ids = request.form.getlist('character_ids[]')
            for cid in character_ids:
                if cid:
                    cc = ChapterCharacter(chapter_id=story.id, character_id=int(cid))
                    db.session.add(cc)

            # 保存发生地区
            region_ids = request.form.getlist('region_ids[]')
            for rid in region_ids:
                if rid:
                    cr = ChapterRegion(chapter_id=story.id, region_id=int(rid))
                    db.session.add(cr)

            # 保存关联阵营（多选）
            faction_ids = request.form.getlist('faction_ids[]')
            for fid in faction_ids:
                if fid:
                    cf = ChapterFaction(chapter_id=story.id, faction_id=int(fid))
                    db.session.add(cf)

            db.session.commit()
            flash('故事保存成功！', 'success')
            return redirect(url_for('story_list'))

        characters = Character.query.filter_by(project_id=current_pid).all()
        all_factions = get_all_factions()
        all_regions = get_all_regions()
        return render_template('story_form.html',
                               story=None,
                               characters=characters,
                               all_factions=all_factions,
                               all_regions=all_regions,
                               selected_characters=[],
                               selected_factions=[],
                               selected_regions=[])

    # 编辑故事
@app.route('/story/<int:story_id>/edit', methods=['GET', 'POST'])
@login_required
def story_edit(story_id):
        current_pid = session.get('current_project_id', 1)
        story = Chapter.query.get_or_404(story_id)
        if request.method == 'POST':
            story.title = request.form.get('title')
            story.description = request.form.get('description')
            story.content = request.form.get('content')

            # 先删旧关联再加新的
            ChapterCharacter.query.filter_by(chapter_id=story.id).delete()
            ChapterRegion.query.filter_by(chapter_id=story.id).delete()
            ChapterFaction.query.filter_by(chapter_id=story.id).delete()

            # 保存登场角色
            character_ids = request.form.getlist('character_ids[]')
            for cid in character_ids:
                if cid:
                    cc = ChapterCharacter(chapter_id=story.id, character_id=int(cid))
                    db.session.add(cc)

            # 保存发生地区
            region_ids = request.form.getlist('region_ids[]')
            for rid in region_ids:
                if rid:
                    cr = ChapterRegion(chapter_id=story.id, region_id=int(rid))
                    db.session.add(cr)

            # 保存关联阵营（多选）
            faction_ids = request.form.getlist('faction_ids[]')
            for fid in faction_ids:
                if fid:
                    cf = ChapterFaction(chapter_id=story.id, faction_id=int(fid))
                    db.session.add(cf)

            db.session.commit()
            flash('故事更新成功！', 'success')
            return redirect(url_for('story_list'))

        characters = Character.query.filter_by(project_id=current_pid).all()
        all_factions = get_all_factions()
        all_regions = get_all_regions()

        selected_characters = [rel.character_id for rel in story.character_relations]
        selected_factions = [rel.faction_id for rel in story.faction_relations]
        selected_regions = [rel.region_id for rel in story.region_relations]

        return render_template('story_form.html',
                               story=story,
                               characters=characters,
                               all_factions=all_factions,
                               all_regions=all_regions,
                               selected_characters=selected_characters,
                               selected_factions=selected_factions,
                               selected_regions=selected_regions)

    # 故事/章节阅读页
@app.route('/story/<int:chapter_id>')
@login_required
def story_detail(chapter_id):
        chapter = Chapter.query.get_or_404(chapter_id)
        prev_chapter = None
        next_chapter = None
        novel = None
        chapter_list = []
        # 如果是长篇下的章节，加载导航数据
        if chapter.story_id:
            novel = chapter.story
            # 按顺序加载所有章节
            chapter_list = novel.chapters.order_by(Chapter.id).all()
            # 找当前章节位置
            current_idx = next(i for i, ch in enumerate(chapter_list) if ch.id == chapter.id)
            if current_idx > 0:
                prev_chapter = chapter_list[current_idx - 1]
            if current_idx < len(chapter_list) - 1:
                next_chapter = chapter_list[current_idx + 1]
        return render_template('story_detail.html',
                               chapter=chapter,
                               novel=novel,
                               chapter_list=chapter_list,
                               prev_chapter=prev_chapter,
                               next_chapter=next_chapter)

    # ==================== 启动程序 ====================
if __name__ == '__main__':
        app.run(debug=True, port=5000)