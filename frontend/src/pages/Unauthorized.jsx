import { Container, Button, ButtonGroup } from "react-bootstrap";
import { Link } from "react-router-dom";

const Unauthorized = () => {
  return (
    <Container className="text-center my-5">
      <h1 className="display-4">401 -- Unauthorized</h1>
      <p className="lead">Доступно только авторизованным пользователям</p>
      <ButtonGroup>
        <Button as={Link} to="/login" variant="primary">
          Войти
        </Button>
        <Button as={Link} to="/" variant="secondary">
          На главную
        </Button>
      </ButtonGroup>
    </Container>
  );
};

export default Unauthorized;
