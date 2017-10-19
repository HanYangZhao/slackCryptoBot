import time
from flask import request, Flask, abort, send_from_directory
import coinmarkets
from celery import Celery
#import jsonencoder
# The parameters included in a slash command request (with example values):
#   token=gIkuvaNzQIHg97ATvDxqgjtO
#   team_id=T0001
#   team_domain=example
#   channel_id=C2147483705
#   channel_name=test
#   user_id=U2147483697
#   user_name=Steve
#   command=/weather
#   text=94070
#   response_url=https://hooks.slack.com/commands/1234/5678

app = Flask(__name__,static_url_path='')
bot = coinmarkets.coinmarkets(app)

commandList = ('updatecoin','alert','buy','sell','topten','gainers','losers','symbols','removealert','showalert')

@app.route('/slack', methods=['POST'])
def slack():
    """Parse the command parameters, validate them, and respond.
    Note: This URL must support HTTPS and serve a valid SSL certificate.
    """
    # Parse the parameters you need
    token = request.form.get('token', None)  # TODO: validate the token
    command = str(request.form.get('command', None))
    responseUrl = str(request.form.get('response_url', None))
    username = str(request.form.get('user_name', None))
    parseCommand = command[1:]

    text = request.form.get('text', None)
    # Validate the request parameters
    if not token:  # or some other failure condition
        abort(400)
    # Use one of the following return statements
    # 1. Return plain text
    if parseCommand in commandList:
        if parseCommand == 'buy' or parseCommand == 'sell':
            return 'not yet implemented'
        else:
            return bot.parseCommand(parseCommand,str(text),responseUrl,username)
    else: 
        return 'invalid command try again'
@app.route('/removealert/<path:path>',methods=['GET'])

def removeAlert(path):
    args = path + " empty"
    return bot.parseCommand('removealert',args,"empty","empty")
    
@app.route('/images/<path:path>', methods=['GET'])
def image(path):
     return send_from_directory('images', path)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=7000, use_reloader=False, threaded=True, ssl_context=('/YOURPATH/fullchain.pem', '/YOURPATH/privkey.pem'))





    # 2. Return a JSON payload
    # See https://api.slack.com/docs/formatting and
    # https://api.slack.com/docs/attachments to send richly formatted messages
    # return jsonify({
    #     # Uncomment the line below for the response to be visible to everyone
    #     # 'response_type': 'in_channel',
    #     'text': 'More fleshed out response to the slash command',
    #     'attachments': [
    #         {
    #             'fallback': 'Required plain-text summary of the attachment.',
    #             'color': '#36a64f',
    #             'pretext': 'Optional text above the attachment block',
    #             'author_name': 'Bobby Tables',
    #             'author_link': 'http://flickr.com/bobby/',
    #             'author_icon': 'http://flickr.com/icons/bobby.jpg',
    #             'title': 'Slack API Documentation',
    #             'title_link': 'https://api.slack.com/',
    #             'text': 'Optional text that appears within the attachment',
    #             'fields': [
    #                 {
    #                     'title': 'Priority',
    #                     'value': 'High',
    #                     'short': False
    #                 }
    #             ],
    #             'image_url': 'http://my-website.com/path/to/image.jpg',
    #             'thumb_url': 'http://example.com/path/to/thumb.png'
    #         }
    #     ]
    # })
    # 3. Send up to 5 responses within 30 minutes to the response_url
    # Implement your custom logic here


    