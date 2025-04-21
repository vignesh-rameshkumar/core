import { useState } from "react"
import BirthdayBlast from "../Components/BirthdayWish"
import Footer from "../Components/Footer"
import Header from "../Components/Header"
import MainPage from "../Components/MainPage"

const Desk = () => {
    const [showGreetings, setShowGreetings] = useState(false);
    return (
        <div className=" h-screen">
            {showGreetings &&
                <div className=""><BirthdayBlast setShowBlast={setShowGreetings} /></div>}
            <Header setShowGreetings={setShowGreetings} />
            <MainPage />
            <Footer />
        </div>
    )
}

export default Desk