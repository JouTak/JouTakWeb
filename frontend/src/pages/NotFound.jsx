import { Container, Button } from "react-bootstrap";
import { Link } from "react-router-dom";

const NotFound = () => {
  return (
    <Container className="text-center my-5">
      <h1 className="display-4">404</h1>
      <p className="lead">Страница не найдена</p>
      <Button as={Link} to="/" variant="primary">
        Вернуться на главную
      </Button>
    </Container>
  );
};

export default NotFound;
