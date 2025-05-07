const AWS = require('aws-sdk');
const dynamo = new AWS.DynamoDB.DocumentClient();

exports.handler = async (event) => {
  const { httpMethod, path, body, pathParameters } = event;
  const tableName = process.env.TABLE_NAME;

  try {
    const data = body ? JSON.parse(body) : {};

    switch (`${httpMethod} ${path}`) {
      case 'POST /usuarios':
        await dynamo.put({ TableName: tableName, Item: data }).promise();
        return { statusCode: 201, body: JSON.stringify(data) };

      case 'GET /usuarios/{id}':
        const user = await dynamo.get({ TableName: tableName, Key: { id: pathParameters.id } }).promise();
        return { statusCode: 200, body: JSON.stringify(user.Item) };

      case 'PUT /usuarios/{id}':
        await dynamo.update({
          TableName: tableName,
          Key: { id: pathParameters.id },
          UpdateExpression: 'set #n = :name',
          ExpressionAttributeNames: { '#n': 'name' },
          ExpressionAttributeValues: { ':name': data.name },
        }).promise();
        return { statusCode: 200, body: JSON.stringify({ id: pathParameters.id, ...data }) };

      case 'DELETE /usuarios/{id}':
        await dynamo.delete({ TableName: tableName, Key: { id: pathParameters.id } }).promise();
        return { statusCode: 204 };

      default:
        return { statusCode: 404, body: 'Ruta no encontrada' };
    }
  } catch (error) {
    return { statusCode: 500, body: JSON.stringify(error.message) };
  }
};