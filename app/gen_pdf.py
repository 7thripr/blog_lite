from weasyprint import HTML
from jinja2 import Template
from flask import make_response, send_file
from app.models import User



html_template = Template("""
    <html>
      <body>
      	<img class="rounded-circle account-img" src="{{ profile_photo }}">
        <h1>User Profile</h1>
        <p>Username: {{ user.username }}</p>
        <p>Email: {{ user.email }}</p>
        <p>Follower Count: {{ user.follower_count }}</p>
        <p>Blog Count: {{ user.blog_count }}</p>
      </body>
    </html>
    """)

def create_pdf(username):
    user = User.query.filter_by(username=username).first()
    html_content = html_template.render(user=user)
    HTML(string=html_content).write_pdf('output.pdf')
    pdf_file = 'output.pdf'
    # response = make_response(send_file(pdf_file, attachment_filename=f'{user}_profile.pdf', as_attachment=True))
    response = make_response(send_file(pdf_file, as_attachment=True, attachment_filename=f'{user}_profile.pdf'))
    response.headers['Content-Type'] = 'application/pdf'
    return response