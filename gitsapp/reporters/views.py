import os
from flask import render_template, url_for, flash, redirect, request, Blueprint
from flask_login import login_user, current_user, logout_user
from gitsapp import db, login_required, app
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from gitsapp.models import User, Report, Report_Image
from gitsapp.reporters.forms import RegistrationForm,LoginForm, CCIEReportForm
from gitsapp import gmap

#reporter flow
reporters_users = Blueprint('reporters_users',__name__)

#create reporter acc

@reporters_users.route('/register_reporter',methods=['GET','POST'])
def register_reporter():
    form = RegistrationForm(request.form)

    if form.validate_on_submit():
        reporter = User(email=form.email.data,password=form.password.data, urole="WORKER")
        db.session.add(reporter)
        db.session.commit()
        
        return redirect(url_for('reporters_users.login_reporter'))
    return render_template('Reporters/register_reporter.html',form=form)


#login
@reporters_users.route('/login_reporter',methods=['GET','POST'])
def login_reporter():
    if current_user.is_authenticated:
        if(current_user.urole == "WORKER"):
            return redirect(url_for('reporters_users.dash'))

    
    form = LoginForm(request.form)
    if form.validate_on_submit():
       
        reporter = User.query.filter_by(email=form.email.data).first()

        if(reporter == None or reporter.urole == "LAW"):
            form.email.errors.append("This is a Law Enforcement account. Use the Law Enforcement  login to use this account")
            return render_template('Reporters/login_reporter.html',form=form, status=200)
        
        if reporter and reporter.check_pwd(form.password.data):
            login_user(reporter)
            return redirect(url_for('reporters_users.dash'))

   
    return render_template('Reporters/login_reporter.html',form=form, status=200)


#after login users should be directed to DASH
@reporters_users.route('/reporter/dash', methods=['GET'])
#@login_required(role="WORKER")
def dash():
    return render_template('Reporters/reporter_dash.html', curr_user = current_user)


@reporters_users.route('/reporter/ccie',methods=['GET','POST'])
@login_required(role="WORKER")
def ccie_report():
    form = CCIEReportForm()
    #if form submitted create a report
    if form.validate_on_submit():  
        #Save images
        img_list=[]
        directory = os.path.join(app.config['STATIC'], 'report_photos')
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        #Find GPS coordinates
        result = gmap.geocode(form.street_address.data)
        #basic check to make sure address matches state
        if(result == None or result[0].get("address_components")[5].get("long_name") != form.state.data):
            form.street_address.errors.append('Address does not match the state provided. Ensure the address entered has no abbreviations (Ex. Drive not Dr. )')
            return render_template('Reporters/CCIE_report.html', form=form)

        
        report = Report(
                        first_name = form.first_name.data,
                        last_name = form.last_name.data,
                        supervisor_fname=form.sup_fname.data,
                        supervisor_lname=form.sup_lname.data,
                        crew_id=form.crew.data,
                        date_of_incident=form.date.data,
                        scale_of_cleanup=form.cleanup.data,
                        type_of_building=form.building_type.data,
                        street_address=form.street_address.data,
                        zipcode=form.zipcode.data,
                        state = form.state.data,
                        gps_lat = result[0].get("geometry").get("location").get("lat"),
                        gps_lng = result[0].get("geometry").get("location").get("lng"),
                        cross_street = form.cross_street.data,
                        notes=form.notes.data,
                        is_hotspot=False
        )
        db.session.add(report)
        db.session.commit()

        
        for image in form.photos.data:
            if image:
                filename=secure_filename(image.filename)   
                file_path = os.path.join(directory, filename)
                image.save(file_path)
                rep_image = Report_Image(file_path, report.id, filename)
                db.session.add(rep_image)
                db.session.commit()
                img_list.append(rep_image)

        report.images = img_list
        db.session.commit()
        return redirect(url_for('reporters_users.dash'))

    #otherwise show the form
    return render_template('Reporters/CCIE_report.html',form=form)

@reporters_users.route('/reporter/sign_out')
@login_required(role="WORKER")
def signout_reporter():
    logout_user()
    return redirect(url_for('core.index'))

#query all the reports created by the user, else give 403 unauth access
@reporters_users.route('/reporter/reports',methods=['GET','POST'])
@login_required(role="WORKER")
def reports(report_id):
    report = Report.query.get_or_404(report_id)
    return render_template('reports.html',report=report)
            
