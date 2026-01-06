from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- CONFIGURAÇÕES DE SEGURANÇA ---
app.config['SECRET_KEY'] = 'uma-chave-secreta-bem-dificil' # Necessário para o Login funcionar
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///produtos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Se não estiver logado, manda pra cá

# --- MODELOS DO BANCO DE DADOS ---

# Tabela de Usuários (NOVO)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True)
    password = db.Column(db.String(80)) # Guardará a senha criptografada

# Tabela de Produtos
class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chamada = db.Column(db.String(300))
    descricao = db.Column(db.String(500))
    valor = db.Column(db.String(50), nullable=False)
    frete_gratis = db.Column(db.Boolean, default=False)
    link_foto = db.Column(db.String(500))
    link_compra = db.Column(db.String(500), nullable=False)
    cupom = db.Column(db.String(50))
    variacao_nome = db.Column(db.String(50))
    variacao_link = db.Column(db.String(500))

# Função obrigatória do Flask-Login para carregar o usuário
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Criar banco e criar usuário ADMIN padrão
with app.app_context():
    db.create_all()
    # Verifica se já existe usuário, se não, cria o Admin
    if not User.query.filter_by(username='admin').first():
        senha_criptografada = generate_password_hash('admin', method='pbkdf2:sha256')
        novo_usuario = User(username='admin', password=senha_criptografada)
        db.session.add(novo_usuario)
        db.session.commit()
        print("--- USUÁRIO ADMIN CRIADO (Login: admin / Senha: admin) ---")

# --- ROTAS DE LOGIN ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        # Verifica se usuário existe e se a senha bate com o hash
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', erro="Usuário ou senha incorretos!")
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- ROTAS DO SISTEMA (Agora Protegidas com @login_required) ---

@app.route('/', methods=['GET', 'POST'])
@login_required  # <--- Bloqueia acesso sem login
def index():
    if request.method == 'POST':
        novo_produto = Produto(
            chamada=request.form['chamada'],
            descricao=request.form['descricao'],
            valor=request.form['valor'],
            frete_gratis='frete_gratis' in request.form,
            link_foto=request.form['link_foto'],
            link_compra=request.form['link_compra'],
            cupom=request.form['cupom'],
            variacao_nome=request.form['variacao_nome'],
            variacao_link=request.form['variacao_link']
        )
        db.session.add(novo_produto)
        db.session.commit()
        return redirect(url_for('index'))

    produtos = Produto.query.order_by(Produto.id.desc()).all()
    return render_template('index.html', produtos=produtos, usuario=current_user.username)

@app.route('/gerar_mensagem', methods=['POST'])
@login_required
def gerar_mensagem():
    ids_selecionados = request.json.get('ids', [])
    produtos = Produto.query.filter(Produto.id.in_(ids_selecionados)).all()
    
    texto_final = ""
    for prod in produtos:
        linha_frete = "📦 Frete Grátis todo o Brasil\n\n" if prod.frete_gratis else ""
        linha_cupom = f"\n➡ Use o cupom: {prod.cupom}" if prod.cupom else ""
        linha_variacao = f"\n\n{prod.variacao_nome}: {prod.variacao_link}" if prod.variacao_nome and prod.variacao_link else ""

        msg = (
            f"{prod.chamada}\n\n{linha_frete}• {prod.descricao}\n\n🔥 R$ {prod.valor}\n\n🛒 {prod.link_compra}{linha_cupom}{linha_variacao}\n\n__________________________\n\n"
        )
        texto_final += msg

    return jsonify({'mensagem': texto_final})

@app.route('/deletar/<int:id>')
@login_required
def deletar(id):
    produto = Produto.query.get_or_404(id)
    db.session.delete(produto)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)