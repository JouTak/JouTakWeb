import {Footer} from '@gravity-ui/navigation';

const CustomFooter = () => {
    return (
        <Footer
            className="page-footer"
            withDivider={false}
            moreButtonTitle="Show more"
            copyright={`@ ${new Date().getFullYear()} "JouTak"`}
            logo={{
                // icon: logoIcon,
                iconSize: 24,
                text: 'JouTak'
            }}
            menuItems={[
                {
                    text: 'Политика конфиденциальности',
                    href: '/privacy-policy',
                    target: 'blank',
                },
                {
                    text: 'Условия использования',
                    href: '/privacy-policy',
                    target: 'blank',
                },
                {
                    text: 'Контакты',
                    href: '/contact',
                    target: 'blank',
                },
            ]}
        />
    )
}

export default CustomFooter;