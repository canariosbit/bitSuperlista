from flask import Flask, render_template, g, request, session, redirect, flash, url_for, make_response
import sqlite3
import bcrypt

app = Flask(__name__)  # Aplicacion del servidor


# Semilla para encriptacion de passwords
semilla = b'$2b$12$AAbdub6epHJ.1dHCta1rmu'


# conecta DB y retorna puntero
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('database1.db')
    return db


# desconecta DB
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def conectar_db():
    return sqlite3.connect('database1.db')


def getAllProductosAdmin():
    # Consultando los productos
    g.db = conectar_db()
    consulta = 'SELECT * FROM Productos WHERE (PropietarioId= 0)'
    cur = g.db.execute(consulta)
    productos = [dict(pro_id=row[0], cat_id=row[1], pro_nombre=row[2])
                 for row in cur.fetchall()]
    g.db.close()
    return productos


def getAllProductosUsuarios():
    # Consultando los productos
    g.db = conectar_db()
    consulta = 'SELECT * FROM Productos WHERE (PropietarioId= ?)'
    if 'nombre' in session:
        id = session['id']

    cur = g.db.execute(consulta, [id])

    productos_usuarios = [dict(pro_id=row[0], cat_id=row[1], pro_nombre=row[2])
                          for row in cur.fetchall()]
    g.db.close()
    return productos_usuarios


def getAllCategorias():
    cantCarrito()
    # Consultando las categorias
    g.db = conectar_db()
    cur = g.db.execute('SELECT * FROM Categorias')

    categorias = [dict(cat_id=row[0], cat_nombre=row[1])
                  for row in cur.fetchall()]
    g.db.close()
    return categorias


def getAllCesta():
    # Consultando los productos
    if 'nombre' in session:
        id = session['id']
    else:
        try:
            id = int(request.cookies.get('visitanteId'))
        except:
            return redirect('/del_cookie')
    g.db = conectar_db()
    consulta = 'SELECT * FROM Cesta WHERE (Id_usuario = ?)'
    cur = g.db.execute(consulta, [id])
    items = [dict(Id=row[0], Id_Usuario=row[1], Item_nombre=row[2], Tachar=row[3], ProductoId=row[4])
             for row in cur.fetchall()]
    g.db.close()
    return items


def cantCarrito():
    if 'nombre' in session:
        id_usuario = session['id']
    else:
        try:
            id_usuario = int(request.cookies.get('visitanteId'))
        except:
            return redirect('/del_cookie')
    db = get_db()
    cur = db.cursor()
    # Consultando si ya existe dentro del Carrito
    find_prod = (
        "SELECT COUNT(Id) FROM Cesta WHERE Id_Usuario = ?")
    cur.execute(find_prod, [(id_usuario)])
    resultado = cur.fetchone()
    session['carrito'] = resultado[0]
    # print(resultado)
    # print(session['carrito'])
    return session['carrito']


@app.route('/set_cookie')
def visitante():
    visitanteId = request.cookies.get('visitanteId')
    # print(visitanteId)
    if visitanteId == None:
        visitanteId = bcrypt.gensalt()
        db = get_db()
        cur = db.cursor()
        (cur.execute("INSERT INTO Usuarios (Nombre, Apellido, Email"
                     ", Contrasena, Admin) VALUES(?,?,?,?,?)", (visitanteId,
                                                                "guest", visitanteId, visitanteId, (-1))))
        db.commit()
        find_user = ("SELECT Id FROM Usuarios WHERE Nombre = ?")
        cur.execute(find_user, [visitanteId])
        resultado = cur.fetchone()
        db.close()
        # print(resultado[0])
        resStr = str(resultado[0])
        redirect_to_index = redirect('/')
        response = app.make_response(redirect_to_index)
        response.set_cookie('visitanteId', resStr)
        # print("cookie seteada")
        return response
    else:
        return redirect('/')


# @app.route('/get_cookie')
# def get_cookie():
#     datos = request.cookies.get('cookie_name')
#     if datos!=None:
#         return datos
#     else:
#         return "No hay cookie"

@app.route('/del_cookie')
def del_cookie():
    redirect_to_index = redirect('/')
    response = app.make_response(redirect_to_index)
    response.set_cookie('visitanteId', value='', expires=0)
    return response


@app.route('/')  # ruta para el home
def home():
    # Consultando las categorias
    categorias = getAllCategorias()

    if 'nombre' in session:
        # Consultando los productos
        productos = getAllProductosUsuarios()
        # Consultando los productos en la cesta
        CestaArticulos = getAllCesta()
        return render_template('home_logged_in.html', categorias=categorias,
                               productos=productos, CestaArticulos=CestaArticulos)
    else:
        visitanteId = request.cookies.get('visitanteId')
        # print("VisitanteId: ", visitanteId)
        if visitanteId == None:
            return redirect('/set_cookie')

        # Consultando los productos
        productos = getAllProductosAdmin()
        CestaArticulos = getAllCesta()
        return render_template('home.html', categorias=categorias,
                               productos=productos, CestaArticulos=CestaArticulos)


@app.route('/AddArt/<string:articulo>/<int:idArticulo>', methods=['GET'])
def AddArt(articulo, idArticulo):
    if 'nombre' in session:
        id_usuario = session['id']
    else:
        try:
            id_usuario = int(request.cookies.get('visitanteId'))
        except:
            return redirect('/del_cookie')

    db = get_db()
    cur = db.cursor()
    # Consultando si ya existe dentro del Carrito
    find_prod = (
        "SELECT * FROM Cesta WHERE Item = ? AND Id_Usuario = ?")
    cur.execute(find_prod, [(articulo), (id_usuario)])
    resultado = cur.fetchone()
    if resultado:
        flash("El artículo ya fue agregado.", "alert-warning")
        return redirect('/')
    (cur.execute("INSERT INTO Cesta (Id_Usuario, Item, Tachar, ProductoId) VALUES(?,?,?,?)",
                 (id_usuario, articulo, 0, idArticulo)))
    db.commit()
    db.close()
    flash("Producto agregado correctamente.", "alert-success")
    return redirect('/')


# Ruta para eliminar articulos de la cesta
@app.route('/DeleteArtCesta/<id>', methods=['GET', 'POST'])
def DeleteArtCesta(id):
    if 'nombre' in session:
        id_usuario = session['id']
    else:
        try:
            id_usuario = int(request.cookies.get('visitanteId'))
        except:
            return redirect('/del_cookie')
    id = int(id)
    db = get_db()
    cur = db.cursor()
    delete_product = ("DELETE FROM Cesta WHERE Id = ? AND Id_Usuario = ?")
    cur.execute(delete_product, [(id), (id_usuario)])
    db.commit()
    db.close()
    return redirect("/cart")

# Ruta para eliminar articulos de la cesta
@app.route('/DeleteArtContenido/<id>', methods=['GET', 'POST'])
def DeleteArtContenido(id):
    if 'nombre' in session:
        id_usuario = session['id']
    else:
        try:
            id_usuario = int(request.cookies.get('visitanteId'))
        except:
            return redirect('/del_cookie')
    id = int(id)
    db = get_db()
    cur = db.cursor()
    delete_product = ("DELETE FROM Contenido WHERE Id = ? AND Id_Usuario = ?")
    cur.execute(delete_product, [(id), (id_usuario)])
    db.commit()
    db.close()
    return redirect("/EditarLista")

# Ruta para eliminar todos los articulos de la cesta
@app.route('/deleteAllCesta', methods=['GET', 'POST'])
def deleteAllCesta():
    if 'nombre' in session:
        id_usuario = session['id']
    else:
        id_usuario = -1
    db = get_db()
    cur = db.cursor()
    delete_product = ("DELETE FROM Cesta WHERE Id_Usuario = ?")
    cur.execute(delete_product, [(id_usuario)])
    db.commit()
    db.close()
    return redirect("/cart")


# Ruta para guardar la cesta en una lista nueva
@app.route('/guardarLista', methods=['GET', 'POST'])
def guardarLista():
    if 'nombre' in session:
        NameLista = request.form['nmlista']
        Descripcion = request.form['descripcion']
        idUsuario = session['id']
        cesta = getAllCesta()
        db = get_db()
        cur = db.cursor()
        consulta = ("SELECT COUNT(Id) FROM Listas WHERE UsuarioId = ?")
        cur.execute(consulta, [idUsuario])
        resultado = cur.fetchone()
        # print("cant listas= " + str(resultado[0]))
        nombreLista = NameLista + '  ' + str(resultado[0]+1)
        consulta = (
            "INSERT INTO Listas (UsuarioId, Nombre, Descripcion) VALUES(?,?,?)")
        cur.execute(consulta, [idUsuario, nombreLista, Descripcion])
        db.commit()
        findListaId = ("SELECT Id FROM Listas WHERE Nombre = ?")
        cur.execute(findListaId, [(nombreLista)])
        result = cur.fetchone()
        idLista = result[0]
        for producto in cesta:
            insertProducto = ("INSERT INTO Contenido (ListaId, ProductoId)\
                VALUES(?,?)")
            cur.execute(insertProducto, [idLista, producto["ProductoId"]])
        flash(nombreLista + " creada con éxito.", "alert-success")
        db.commit()
        db.close()
    return redirect("/cart")


# Ruta para eliminar articulos de la cesta y volver al home
@app.route('/DeleteArtCesta_home/<id>', methods=['GET', 'POST'])
def DeleteArtCesta_home(id):
    if 'nombre' in session:
        id_usuario = session['id']
    else:
        try:
            id_usuario = int(request.cookies.get('visitanteId'))
        except:
            return redirect('/del_cookie')
    id = int(id)
    db = get_db()
    cur = db.cursor()
    delete_product = ("DELETE FROM Cesta WHERE Id = ? AND Id_Usuario = ?")
    cur.execute(delete_product, [(id), (id_usuario)])
    db.commit()
    db.close()
    return redirect("/")


@app.route('/adquirido/<id>')  # Marcar/desmarcar artículo en carrito
def tacharToggle(id):
    if 'nombre' in session:
        id_usuario = session['id']
    else:
        try:
            id_usuario = int(request.cookies.get('visitanteId'))
        except:
            return redirect('/del_cookie')
    db = get_db()
    cur = db.cursor()
    # Consultando si ya existe dentro del Carrito
    find_prod = (
        "SELECT Tachar FROM Cesta WHERE Id_Usuario = ? AND Id = ?")
    cur.execute(find_prod, [(id_usuario), (id)])
    resultado = cur.fetchone()
    # print("resultadox: ")
    # print(resultado[0])

    if (resultado[0]) == 1:
        estado = 0
    else:
        estado = 1
    sql = (
        'UPDATE Cesta SET Tachar=?  WHERE id=?')
    cur.execute(sql, [(estado), (id)])
    db.commit()
    # db.close()
    return redirect(url_for('cart'))


@app.route('/cart')  # Ruta Mi Cesta
def cart():
    cantCarrito()
    if 'nombre' in session:
        # Consultando los item de la tabla Cesta
        items = getAllCesta()
        g.db.close()
        return render_template('carrito.html', items=items)
    else:
        items = getAllCesta()
        g.db.close()
        return render_template('carrito_home.html', items=items)


# ingreso de usuarios nuevos
# Ruta de la pagina registro
@app.route('/registrar_usuario', methods=['POST'])
def registrar_usuario():
    if request.method == "POST":
        nombre = request.form['nmNombre']
        apellido = request.form['nmApellido']
        email = request.form['nmCorreo']
        password = request.form["nmPwd"]
        passwordRep = request.form["nmPwdnewRep"]
        if (password == passwordRep):
            if len(password) < 8:
                flash("La contraseña debe tener al menos 8 caracteres.",
                      "alert-warning")
                return render_template('registro_usuario.html', nombre=nombre, apellido=apellido, correo=email, success=False)

            password_enc = password.encode("utf-8")
            hashed_pw = bcrypt.hashpw(password_enc, semilla)
            admin = 0
            # print ("Email:"+ email)
            # print("Password:"+ password)
            # print("Password_encriptado:", hashed_pw)

            db = get_db()
            cur = db.cursor()
            find_user = ("SELECT * FROM Usuarios WHERE Email = ?")
            cur.execute(find_user, [(email)])
            resultado = cur.fetchall()  # podria ser fetchone()
            if resultado:
                texto = "El correo " + email + " ya está registrado."
                flash(texto, "alert-warning")
                return render_template('registro_usuario.html', success=False)

            (cur.execute("INSERT INTO Usuarios (Nombre, Apellido, Email"
                         ", Contrasena, Admin) VALUES(?,?,?,?,?)", (nombre,
                                                                    apellido, email, hashed_pw, admin)))
            db.commit()
            flash("Usuario creado con éxito!! Redireccionando...", "alert-success")

            # cargo los productos iniciales del usuario
            cur = db.cursor()
            find_user = ("SELECT Id FROM Usuarios WHERE Email = ?")
            cur.execute(find_user, [(email)])
            user_id = cur.fetchone()
            productosAdmin = getAllProductosAdmin()
            for producto in productosAdmin:
                cur.execute("INSERT INTO Productos (CategoriaId, Producto, PropietarioId) VALUES(?,?,?)", (
                            producto["cat_id"], producto["pro_nombre"], user_id[0]))

            db.commit()
            db.close()
            return render_template('registro_usuario.html', nombre=nombre, apellido=apellido, correo=email, success=True)
        else:
            flash("Las contraseñas no coinciden!!", "alert-warning")
            return render_template('registro_usuario.html', nombre=nombre, apellido=apellido, correo=email, success=False)


@app.route('/login', methods=['GET', 'POST'])  # Ruta de la pagina login
def login():
    if 'nombre' in session:
        return redirect("/")
    else:
        if request.method == 'POST':
            email = request.form['nmCorreo']
            password = request.form["nmPwd"]
            password_enc = password.encode("utf-8")
            hashed_pw = bcrypt.hashpw(password_enc, semilla)
            # print("Email="+email)
            # print("Psw="+password)
            # print("Hash=", hashed_pw)
            db = get_db()
            cur = db.cursor()
            find_user = (
                "SELECT * FROM Usuarios WHERE Email = ? AND Contrasena = ?")
            cur.execute(find_user, [(email), (hashed_pw)])
            resultado = cur.fetchall()  # podria ser fetchone()
            db.close()
            if resultado:
                # print("Result: "+resultado[0][3])
                session['id'] = resultado[0][0]
                session['nombre'] = resultado[0][1]
                session['correo'] = resultado[0][3]
                flash("Ingresó con éxito!! Redireccionando...", "alert-success")
                return render_template('login.html', success=True)
            else:
                flash("Correo o contraseña incorrectos.", "alert-warning")
                return redirect('/login')
        else:
            return render_template('login.html')


@app.route('/logout')
def fnLogout():
    session.clear()
    return redirect("/")


@app.route('/perfil', methods=['GET', 'POST'])
def fnPerfil():
    if 'nombre' in session:
        correo = session['correo']
        db = get_db()
        cur = db.cursor()
        find_user = (
            "SELECT Id, Nombre, Apellido, Email FROM Usuarios WHERE Email = ?")
        cur.execute(find_user, [(correo)])
        resultado = cur.fetchall()
        db.close()
        id = resultado[0][0]
        nombre = resultado[0][1]
        apellido = resultado[0][2]
        correo = resultado[0][3]
        return render_template('editar_perfil.html', id=id, nombre=nombre, apellido=apellido, correo=correo, succes=False)
    else:
        return redirect("/")


@app.route('/actualizar_usuario', methods=['POST'])
def fnActualizar():
    if 'nombre' in session:
        id = session['id']
        db = get_db()
        cur = db.cursor()
        nombre = request.form['nmNombre']
        apellido = request.form['nmApellido']
        email = request.form['nmCorreo']
        password = request.form["nmPwdnew"]
        passwordRep = request.form["nmPwdnewRep"]

        if request.method == "POST":
            if request.form['submit'] == 'eliminar':
                sql = 'DELETE FROM Productos WHERE PropietarioId=?'
                cur.execute(sql, [(id)])
                db.commit()
                sql = 'DELETE FROM Usuarios WHERE Id=?'
                cur.execute(sql, [(id)])
                db.commit()
                db.close()
                session.clear()
                flash("Usuario ELIMINADO.", "alert-warning")
                return render_template('editar_perfil.html', success=True)

            if (password == passwordRep):
                if len(password) > 0 and len(password) < 8:
                    flash(
                        "La contraseña debe tener al menos 8 caracteres.", "alert-warning")
                    return render_template('editar_perfil.html', id=id, nombre=nombre, apellido=apellido, correo=email, success=False)

                if len(password) > 0:
                    password_enc = password.encode("utf-8")
                    hashed_pw = bcrypt.hashpw(password_enc, semilla)
                    admin = 0
                    sql = (
                        'UPDATE Usuarios SET Nombre=?, Apellido=? , Email=?, Contrasena=?, Admin=?  WHERE id=?')
                    cur.execute(sql, [(nombre), (apellido),
                                      (email), (hashed_pw), (admin), (id)])
                else:
                    sql = (
                        'UPDATE Usuarios SET Nombre=?, Apellido=? , Email=? WHERE id=?')
                    cur.execute(sql, [(nombre), (apellido),
                                      (email), (id)])
                db.commit()
                db.close()
                flash("Usuario actualizado con exito!! Redireccionando...",
                      "alert-success")

                return render_template('editar_perfil.html', success=True)
            else:
                correo = session['correo']
                db = get_db()
                cur = db.cursor()
                find_user = (
                    "SELECT Id, Nombre, Apellido, Email FROM Usuarios WHERE Email = ?")
                cur.execute(find_user, [(correo)])
                resultado = cur.fetchall()
                db.close()
                id = resultado[0][0]
                nombre = resultado[0][1]
                apellido = resultado[0][2]
                correo = resultado[0][3]
                flash("Las contraseñas no coinciden!!", "alert-warning")
                return render_template('editar_perfil.html', id=id, nombre=nombre, apellido=apellido, correo=correo, success=False)
    else:
        return redirect("/")


@app.route('/reset')  # Ruta de la pagina reset
def reset():
    return render_template('reset.html')


@app.route('/registrarse')  # Ruta de la pagina registro
def registrarse():
    return render_template('registro_usuario.html', success=False)


@app.route('/MisListas')  # Ruta Mis Listas
def MisListas():
    if 'nombre' in session:
        id = session['id']
        db = get_db()
        cur = db.cursor()
        find_lists = (
            "SELECT Id, Nombre, Descripcion FROM Listas WHERE UsuarioId = ?")
        cur.execute(find_lists, [(id)])
        resultado = [dict(Id=row[0], Nombre=row[1], Descripcion=row[2])
                     for row in cur.fetchall()]
        db.close()
        return render_template('mis_listas.html', listas=resultado)
    else:
        return redirect("/")


# Ruta para eliminar articulos de la cesta y volver al home
@app.route('/DeleteLista/<id>', methods=['GET', 'POST'])
def DeleteLista(id):
    if 'nombre' in session:
        id_usuario = session['id']
    else:
        id_usuario = -1
    id = int(id)
    db = get_db()
    cur = db.cursor()
    delete_list = ("DELETE FROM Listas WHERE Id = ? AND UsuarioId = ?")
    cur.execute(delete_list, [(id), (id_usuario)])
    db.commit()
    db.close()
    return redirect("/MisListas")


@app.route('/EditarLista/<id>', methods=['GET', 'POST'])
def EditarLista(id):
    if 'nombre' in session:
        id_usuario = session['id']
    else:
        id_usuario = -1
    id = int(id)
    db = get_db()
    cur = db.cursor()
    # Consultado  las listas segun el usuario
    searchAll = (
        "SELECT ListaNombre, Descripcion, ProductoNombre, ProductoId, ContenidoId FROM General WHERE ListaId = ? AND UsuarioId = ?")
    cur.execute(searchAll, [(id), (id_usuario)])
    resultados = [dict(ListaNombre=row[0], Descripcion=row[1], ProductoNombre=row[2], ProductoId=row[3], ContenidoId=row[4])
                  for row in cur.fetchall()]
    db.close()
    return render_template('VerLista.html', datos=resultados)

# Ruta alta y baja de artículos
@app.route('/ABM_articulos', methods=['GET', 'POST'])
def ABM_articulos():
    if 'nombre' in session:
        # Consultando las categorias
        categorias = getAllCategorias()
        # Consultando los productos
        productos = getAllProductosUsuarios()
        #
        if request.method == "POST":
            if 'submit' in request.form:
                articulo = request.form.get("articulo")
                catSelected = request.form.get('categoria')
                # print("articulo: "+(articulo))
                # print("categ: " + (catSelected))
                articulo = articulo.upper()
                catSelected = int(catSelected)
                # Consultando si ya existe dentro de Productos
                db = get_db()
                cur = db.cursor()
                find_prod = (
                    "SELECT * FROM Productos WHERE Producto = ? AND PropietarioId= ?")
                cur.execute(find_prod, [(articulo), (session['id'])])
                resultado = cur.fetchall()  # podria ser fetchone()

                if resultado:
                    catExiste = str(resultado[0][1])
                    # print("el prod ya existe en categ: " + catExiste)
                    flash("El artículo ya fue ingresado", "alert-warning")
                else:
                    if catSelected == 0:
                        # print("Debe seleccionar una categoría.")
                        flash("Debe seleccionar una categoría.", "alert-warning")
                    else:
                        cur.execute("INSERT INTO Productos (CategoriaId, Producto, PropietarioId) VALUES(?,?,?)", (
                            catSelected, articulo, session['id']))
                        db.commit()
                        productos = getAllProductosUsuarios()
                db.close()

            else:
                catSelected = int(request.form.get('updCat'))
                # print("catBoton")
                # print(catSelected)
            if request.form['submit'] == "agregar":
                return render_template('ABM_articulos.html', categorias=categorias, productos=productos, catSelected=catSelected)
            else:
                # cargo lista del carrito
                itemsCarrito = getAllCesta()
                return render_template('home_logged_in.html', categorias=categorias,
                                       productos=productos, items=itemsCarrito)
        else:
            return render_template('ABM_articulos.html', categorias=categorias, productos=productos, catSelected="OTROS")
    else:
        return redirect("/")


@app.route('/deleteArt/<id>', methods=['GET', 'POST'])
def deleteArt(id):
    id = int(id)
    if 'nombre' in session:
        id_usuario = session['id']
    else:
        try:
            id_usuario = int(request.cookies.get('visitanteId'))
        except:
            return redirect('/del_cookie')
    id = int(id)
    db = get_db()
    cur = db.cursor()
    delete_product = (
        "DELETE FROM Productos WHERE Id = ? AND PropietarioId = ?")
    cur.execute(delete_product, [(id), (id_usuario)])
    db.commit()
    db.close()
    flash("Producto eliminado.", "alert-danger")
    return redirect("/")


@app.route('/search/', methods=['GET', 'POST'])
def search():
    productos = getAllProductosUsuarios()
    return render_template("searchTest.html", productos=productos)


if __name__ == '__main__':
    app.secret_key = 'qwerty'
    app.run(debug=True, port=5000)
