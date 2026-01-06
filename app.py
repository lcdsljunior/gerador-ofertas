from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
app.config['SECRET_KEY'] = 'segredo-absoluto'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///produtos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- MODELOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True)
    password = db.Column(db.String(80))

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chamada = db.Column(db.String(300))
    descricao = db.Column(db.String(500))
    valor = db.Column(db.String(50), nullable=False)
    frete_gratis = db.Column(db.Boolean, default=False)
    link_compra = db.Column(db.String(800), nullable=False)
    cupom = db.Column(db.String(50))
    # Removemos 'link_foto' manual para não quebrar o preview oficial

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        senha_hash = generate_password_hash('admin', method='pbkdf2:sha256')
        db.session.add(User(username='admin', password=senha_hash))
        db.session.commit()

# --- ROTAS ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        return render_template('login.html', erro="Dados incorretos")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        novo = Produto(
            chamada=request.form.get('chamada'),
            descricao=request.form.get('descricao'),
            valor=request.form.get('valor'),
            frete_gratis='frete_gratis' in request.form,
            link_compra=request.form.get('link_compra'),
            cupom=request.form.get('cupom')
        )
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('index'))

    produtos = Produto.query.order_by(Produto.id.desc()).all()
    return render_template('index.html', produtos=produtos, usuario=current_user.username)

@app.route('/gerar_mensagem', methods=['POST'])
@login_required
def gerar_mensagem():
    ids = request.json.get('ids', [])
    produtos = Produto.query.filter(Produto.id.in_(ids)).all()
    lista_mensagens = []

    for prod in produtos:
        linha_frete = "📦 Frete Grátis todo o Brasil\n\n" if prod.frete_gratis else ""
        linha_cupom = f"\n➡ Use o cupom: {prod.cupom}" if prod.cupom else ""
        
        # --- LAYOUT EXATO QUE FUNCIONA ---
        # A Mágica: O Link de Compra está no final.
        # O WhatsApp lê o link, gera a Foto (01) e o Nome do Site (02) e coloca no TOPO da bolha.
        
        msg = (
            f"{prod.chamada}\n\n"        # 03
            f"{linha_frete}"             # 04
            f"• {prod.descricao}\n\n"    # 05
            f"🔥 R$ {prod.valor}\n\n"     # 06
            f"🛒 {prod.link_compra}"     # 07 (Gerador da Foto)
            f"{linha_cupom}"
        )
        
        lista_mensagens.append(msg)

    return jsonify({'mensagens': lista_mensagens})

@app.route('/deletar/<int:id>')
@login_required
def deletar(id):
    prod = Produto.query.get_or_404(id)
    db.session.delete(prod)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)