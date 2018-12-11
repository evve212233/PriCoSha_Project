#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
import hashlib

#Initialize the app from Flask
app = Flask(__name__)

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port = 3306,
                       user='root',
                       password=None,
                       db='pricosha',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

#Login/Register - Show public posts that are posted within 24 hours
@app.route('/')
def hello():
    cursor = conn.cursor();
    query = 'SELECT * FROM contentitem WHERE is_pub AND TIMESTAMPDIFF(HOUR, post_time, CURRENT_TIMESTAMP)<=24'
    #query = 'SELECT * FROM contentitem'
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return render_template('index.html', public=data)


# Display shared posts and public posts
@app.route('/home')
def home():
    user = session['email']
    cursor = conn.cursor();
    # Find the posts that are shared with user
    query = 'SELECT * FROM contentitem NATURAL JOIN (SELECT item_id FROM share NATURAL JOIN belong WHERE email = %s)'
    query += ' AS T WHERE item_id=T.item_id ORDER BY post_time DESC'
    cursor.execute(query, user)
    data = cursor.fetchall()

    infoString = []
    for entry in data:
        append = {"post": entry}

        query = 'SELECT fname, lname FROM person NATURAL JOIN (SELECT email_tagged AS email FROM tag WHERE item_id=%s AND status) AS T'
        cursor.execute(query, entry['item_id'])
        taggees = cursor.fetchall()
        tagStr = "TAGGEE(s): |"
        if (taggees):
            for person in taggees:
                tagStr += (person['fname'] + " " + person['lname'] + "|")
        else:
            tagStr += "None|"
        append["taggee"] = tagStr

        query = "SELECT emoji FROM rate WHERE item_id=%s"
        cursor.execute(query, entry['item_id'])
        emojis = cursor.fetchall()
        emojiStr = "RATING(s): |"
        if (emojis):
            for emoji in emojis:
                emojiStr += (emoji['emoji'] + "|")
        else:
            emojiStr += "None|"
        append["emoji"] = emojiStr
        infoString.append(append)

    cursor.close()
    return render_template('home.html', name=session['fname'], info=infoString, public=data)

#Define route for register
@app.route('/register')
def register():
    error = request.args.get('error')
    return render_template("register.html",errors = error)

@app.route("/register/user",methods=['GET','POST'])
def registerUser():
    fname = request.form["fname"]
    lname = request.form["lname"]
    email = request.form["email"]
    pwd = request.form["pwd"]
    secPwd = request.form["2pwd"]
    result = None
    if pwd != secPwd:
        msg = "Your Passwords should match each other"
        return redirect(url_for('register',error=msg))
    if len(email) > 20:
        msg = "Sorry, but email length cannot exceed 20"
        return redirect(url_for('register',error=msg))
    cursor = conn.cursor()
    try:
        sql = "SELECT * FROM person WHERE email=(%s)"
        cursor.execute(sql,(email))
        result = cursor.fetchone()
    finally:
        if not result:
            #pwd = encrypt(pwd)
            sql = "INSERT INTO `person` (`email`,`password`,`fname`,`lname`) VALUES (%s,%s,%s,%s)"
            cursor.execute(sql,(email,pwd,fname,lname))
            conn.commit()
            cursor.close()
            session['user'] = email
            return redirect(url_for('post'))
        else:
            msg = "User Already Exist"
            return redirect(url_for('registerAuth',error=msg))


@app.route('/login')
def login():
    return render_template('index.html')

#Login into Pricosha
@app.route('/loginAuth', methods=['GET', 'POST'])   
def loginAuth():    
    #grabs information from the forms
    email = request.form['email']
    password = request.form['password']
    #query from database
    cursor = conn.cursor()
    query = 'SELECT * FROM Person WHERE email = %s and password = %s'
    #cursor.execute(query, (email, encrypt(password)))
    hashed_pwd = hashlib.sha256(password.encode()).hexdigest() # hash the password
    cursor.execute(query, (email, hashed_pwd))
    #stores the results in a variable
    data = cursor.fetchone() #use fetchall() if you are expecting more than 1 data row
    cursor.close()
    error = None
    if(data):
        #creates a session for the the user session is a built in
        session['email'] = email
        session['fname'] = data['fname']
        session['lname'] = data['lname']
        return redirect(url_for('home'))
    else:
        #returns an error message to the html page
        error = 'Invalid login or email'
        return render_template('index.html', error=error)

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    #grabs information from the forms
    email = request.form['email']
    password = request.form['pwd']
    fname = request.form['fname']
    lname = request.form['lname']
    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM person WHERE email = %s'
    cursor.execute(query, (email))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    error = None
    if(data):
        #If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error = error)
    else:
        ins = 'INSERT INTO person VALUES(%s, %s, %s, %s)'
        hashed_pwd = hashlib.sha256(password.encode()).hexdigest()  # hash the password
        cursor.execute(ins, (email, hashed_pwd, fname, lname))
        conn.commit()
        cursor.close()
        return render_template('index.html')



@app.route('/post', methods=['GET', 'POST'])
def post():
    email = session['email']
    cursor = conn.cursor();
    item_name = request.form['item_name']
    pub = request.form['public']
    if pub == 'public':
        query2 = 'INSERT INTO contentitem (email_post,item_name, is_pub) VALUES (%s,%s,1)'
        cursor.execute(query2,(email, item_name))
        conn.commit()
        cursor.close()
    else:
        query3 = 'INSERT INTO contentitem (email_post,item_name, is_pub) VALUES (%s,%s,0)'
        cursor.execute(query3,(email, item_name))
        conn.commit()
        cursor.close()
    return redirect(url_for('my_posts'))

@app.route('/my_posts', methods=["GET", "POST"])
def my_posts():
    email = session['email']
    cursor = conn.cursor();
    query = 'SELECT item_id, item_name, post_time FROM contentitem WHERE email_post = %s ORDER BY item_id DESC'
    cursor.execute(query, (email))
    data = cursor.fetchall()
    cursor.close()
    return render_template('my_posts.html', name=session['fname'], posts=data)

@app.route('/share_group', methods=["GET", "POST"])
def share_group():
    email = session['email']
    cursor = conn.cursor();
    query = 'SELECT item_id, item_name, post_time FROM contentitem WHERE email_post = %s ORDER BY item_id DESC'
    cursor.execute(query, (email))
    post_data = cursor.fetchall()
    query = 'SELECT fg_name, item_id FROM share WHERE owner_email = %s ORDER BY item_id DESC'
    cursor.execute(query, (email))
    share_data = cursor.fetchall()
    cursor.close()
    return render_template('share_group.html', name=session['fname'], posts=post_data, shares=share_data)

@app.route('/share_to_grp', methods=["GET", "POST"])
def share_to_grp():
    email = session['email']
    cursor = conn.cursor();

    query = 'SELECT item_id, item_name, post_time FROM contentitem WHERE email_post = %s ORDER BY item_id DESC'
    cursor.execute(query, (email))
    post_data = cursor.fetchall()
    query = 'SELECT fg_name, item_id FROM share WHERE owner_email = %s ORDER BY item_id DESC'
    cursor.execute(query, (email))
    share_data = cursor.fetchall()

    share_grp = request.form['group_name']
    item_id = request.form['item_id']
    error = None
    query1 = 'SELECT fg_name FROM friendgroup WHERE owner_email=%s'
    cursor.execute(query1, (email))
    fg_lst = cursor.fetchall()
    #if share_grp not in fg_lst:
    #    error = 'Group does not exist'
    #    return render_template('share_group.html', name=session['fname'], posts=post_data, shares=share_data, email=email, error=error)
    try:
        query = 'INSERT INTO share VALUES (%s, %s, %s)'
        cursor.execute(query, (email, share_grp, item_id))
        conn.commit()
        cursor.close()
        return redirect(url_for('share_group'))
    except:
        # returns an error message to the html page
        error = 'Invalid Share (Already exist)'
        return render_template('share_group.html', name=session['fname'], posts=post_data, shares=share_data, email=email, error=error)

@app.route('/tag_request', methods=["GET", "POST"])
def tag_request():
    email=session['email']
    cursor=conn.cursor()
    query='SELECT * FROM Tag NATURAL JOIN contentitem WHERE Tag.email_tagged = %s AND (status IS NULL or status= false)'
    cursor.execute(query,(email))
    conn.commit()
    data=cursor.fetchall()
    query2='SELECT * FROM Tag NATURAL JOIN contentitem WHERE Tag.email_tagged = %s AND (status=true or status=false)'
    cursor.execute(query2,(email))
    conn.commit()
    data2=cursor.fetchall()
    cursor.close()
    return render_template('tag_request.html',name=session['fname'],pending_request=data, show_tag=data2)

@app.route('/accept_tag', methods=['GET','POST'])
def accept_tag():
     item_id = request.form['item_id']
     email = session['email']
     tagger=request.form['tagger']
     cursor=conn.cursor()
     query='UPDATE Tag SET status=True WHERE email_tagged=%s AND email_tagger=%s AND item_id=%s'
     cursor.execute(query,(email,tagger,item_id))
     conn.commit()
     data=cursor.fetchall()
     cursor.close()
     return redirect(url_for('tag_request'))

@app.route('/decline_tag', methods=['GET','POST'])
def decline_tag():
    item_id = request.form['item_id']
    email = session['email']
    tagger = request.form['tagger']
    cursor = conn.cursor()
    query = 'DELETE FROM Tag WHERE email_tagged=%s AND email_tagger=%s AND item_id=%s'
    cursor.execute(query, (email, tagger, item_id))
    conn.commit()
    cursor.close()
    return redirect(url_for('tag_request'))


@app.route('/tag_other', methods=['GET','POST'])
def tag_other():
    # check that user is logged in
    email = session['email']
    # should throw exception if username not found
    cursor = conn.cursor();

    query3 = 'SELECT * FROM contentitem NATURAL JOIN (SELECT item_id FROM share NATURAL JOIN belong WHERE email = %s)'
    query3 += ' AS T WHERE item_id=T.item_id ORDER BY post_time DESC'
    cursor.execute(query3, email)
    share = cursor.fetchall()

    query1 = 'SELECT * FROM contentitem WHERE is_pub'
    cursor.execute(query1)
    data = cursor.fetchall()
    query2 = 'SELECT * FROM tag WHERE email_tagger = %s'
    cursor.execute(query2,(email))
    data2 = cursor.fetchall()
    cursor.close()
    return render_template('tag_other.html', name=session['fname'], public=data, info=share, tags=data2)


@app.route('/tagee', methods=['GET','POST'])
def tagee():
    email = session['email']
    cursor = conn.cursor();

    query1 = 'SELECT * FROM contentitem WHERE is_pub'
    cursor.execute(query1)
    data1 = cursor.fetchall()
    query2 = 'SELECT * FROM tag WHERE email_tagger = %s'
    cursor.execute(query2,(email))
    data2 = cursor.fetchall()

    query5 = 'SELECT * FROM contentitem NATURAL JOIN (SELECT item_id FROM share NATURAL JOIN belong WHERE email = %s)'
    query5 += ' AS T WHERE item_id=T.item_id ORDER BY post_time DESC'
    cursor.execute(query5, email)
    share = cursor.fetchall()

    query4 = 'SELECT item_id, email_post FROM contentitem WHERE is_pub'
    cursor.execute(query4)
    data3 = cursor.fetchall()
    query3 = 'SELECT item_id, email_post FROM contentitem NATURAL JOIN (SELECT item_id FROM share NATURAL JOIN belong WHERE email = %s)'
    query3 += ' AS T WHERE item_id=T.item_id ORDER BY post_time DESC'
    cursor.execute(query3,(email))
    data4 = cursor.fetchall()

    email_lst = data3+data4
    taggee = request.form['email_tagged']
    item_id = request.form['item_id']
    check_email_id = {'item_id': int(item_id), 'email_post': taggee}
    if check_email_id not in email_lst:
        error = 'You cannot propose this tag'
        return render_template('tag_other.html', name=session['fname'], public=data1, info=share, tags=data2, error=error)

    try:
        query = 'INSERT INTO tag (email_tagged, email_tagger, item_id) VALUES (%s, %s, %s)'
        cursor.execute(query, (taggee, email, item_id))
        conn.commit()
        cursor.close()
        return redirect(url_for('tag_other'))
    except:
        error = 'Invalid tag'
        return render_template('tag_other.html', name=session['fname'], public=data1, tags=data2, info=share, error=error)

@app.route('/logout')
def logout():
    session.pop('email')
    return redirect('/')

@app.route("/addFriend", methods=['GET','POST'])
def addFriend():
    owner_email = session['email']
    fst_name = request.form['fname']
    lst_name = request.form['lname']
    fgroup = request.form['fgroup']
    cursor = conn.cursor();
    session['friend_fname']=fst_name
    session['friend_lname']=lst_name
    session['fgroup']=fgroup
    query0 = 'SELECT * FROM friendgroup WHERE owner_email=%s'
    cursor.execute(query0,(owner_email))
    conn.commit()
    pub_fg = cursor.fetchall()

    query1 = 'SELECT email FROM person WHERE fname=%s AND lname=%s'
    cursor.execute(query1,(fst_name,lst_name))
    email_lst = cursor.fetchall()
    num_email = len(email_lst)

    if num_email==0:
        error = 'Person does not exist'
        cursor.close()
        return render_template('friend_groups.html', name=session['fname'], public=pub_fg, error=error)
    try:
        if num_email==1:
            query2='INSERT INTO belong VALUES (%s, %s, %s)'
            cursor.execute(query2,(email_lst[0]['email'], owner_email, fgroup))
            conn.commit()
            cursor.close()
            return redirect(url_for('friend_groups'))
        elif num_email>1:
            return redirect(url_for('multi_friends'))
    except:
        error = 'Invalid tag'
        return render_template('friend_groups.html', name=session['fname'], public=pub_fg, error=error)

@app.route('/multi_friends', methods=["GET", "POST"])
def multi_friends():
    email = session['email']
    # check that user is logged in
    username = session['fname']
    # should throw exception if username not found
    cursor = conn.cursor();
    query = 'SELECT email FROM person WHERE fname=%s AND lname=%s'
    cursor.execute(query, (session['friend_fname'], session['friend_lname']))
    data = cursor.fetchall()
    print(data)
    cursor.close()
    return render_template('select_email.html', name=username, email_list=data)

@app.route('/chosen_friend', methods=["GET", "POST"])
def chosen_friend():
    owner_email = session['email']
    f_email = request.args['f_email']
    cursor = conn.cursor();
    query = 'INSERT INTO belong VALUES (%s, %s, %s)'
    cursor.execute(query, (f_email, owner_email, session['fgroup']))
    conn.commit()
    cursor.close()
    return redirect(url_for('friend_groups'))
@app.route('/friend_groups', methods=["GET", "POST"])
def friend_groups():
    # check that user is logged in
    email = session['email']
    # should throw exception if username not found
    cursor = conn.cursor();
    query1 = 'SELECT * FROM friendgroup WHERE owner_email=%s'
    cursor.execute(query1,(email))
    conn.commit()
    data = cursor.fetchall()
    cursor.close()
    return render_template('friend_groups.html', name=session['fname'], public=data)


app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)
