import Forbidden from "./Forbidden"

export default function Restricted() {
  const hasAccess = false

  if (!hasAccess) {
    return <Forbidden />
  }

  return (
    <div className="restricted-page">
      <h1>restricted</h1>
      <p>доступ разрешен! добро пожаловать на секретную страничку!</p>
    </div>
  )
}